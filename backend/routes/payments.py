"""
RealtouchHR - Payment Routes (Stripe Integration)
SaaS Subscription Billing API

Endpoints for subscription management and payments.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class SubscriptionCheckoutRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID: starter, professional, or enterprise")
    origin_url: str = Field(..., description="Frontend origin URL for redirects")


class AddonCheckoutRequest(BaseModel):
    addon_id: str
    origin_url: str
    quantity: int = Field(default=1, ge=1)


class CheckStatusRequest(BaseModel):
    session_id: str
    origin_url: str


class PayslipCheckoutRequest(BaseModel):
    payslip_id: str
    origin_url: str


# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> User:
    """Get current authenticated user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=401, detail="User not found")
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def require_owner(request: Request) -> User:
    """Require owner role for billing"""
    user = await get_current_user(request)
    if user.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only company owner can manage billing"
        )
    return user


# ==================== PAYMENT ROUTES ====================

@router.get("/plans")
async def get_subscription_plans(user: User = Depends(get_current_user)):
    """
    Get available subscription plans.
    """
    from services.payment_service import SUBSCRIPTION_PLANS, ADDONS
    
    return {
        "plans": SUBSCRIPTION_PLANS,
        "addons": ADDONS
    }


@router.get("/billing")
async def get_billing_info(user: User = Depends(require_owner)):
    """
    Get company billing information and transaction history.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    try:
        from services.payment_service import payment_service, SUBSCRIPTION_PLANS, ADDONS
        billing = await payment_service.get_company_billing(user.company_id)
        return billing
    except Exception as exc:
        logger.warning("Billing info fetch failed for %s: %s", user.company_id, exc)
        from services.payment_service import SUBSCRIPTION_PLANS, ADDONS
        return {
            "company_id": user.company_id,
            "current_plan": None,
            "subscription_active": False,
            "employee_limit": 10,
            "transactions": [],
            "available_plans": SUBSCRIPTION_PLANS,
            "available_addons": ADDONS,
        }


@router.post("/checkout/subscription")
async def create_subscription_checkout(
    request_data: SubscriptionCheckoutRequest,
    user: User = Depends(require_owner)
):
    """
    Create a Stripe checkout session for subscription.
    
    Frontend should provide origin_url (window.location.origin).
    Amount is determined server-side from predefined plans.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.payment_service import payment_service
    
    try:
        result = await payment_service.create_subscription_checkout(
            plan_id=request_data.plan_id,
            company_id=user.company_id,
            user_id=user.user_id,
            user_email=user.email,
            origin_url=request_data.origin_url
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkout/addon")
async def create_addon_checkout(
    request_data: AddonCheckoutRequest,
    user: User = Depends(require_owner)
):
    """
    Create a Stripe checkout session for add-on purchase.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.payment_service import payment_service
    
    try:
        result = await payment_service.create_addon_checkout(
            addon_id=request_data.addon_id,
            company_id=user.company_id,
            user_id=user.user_id,
            user_email=user.email,
            origin_url=request_data.origin_url,
            quantity=request_data.quantity
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkout/status")
async def check_checkout_status(
    request_data: CheckStatusRequest,
    user: User = Depends(get_current_user)
):
    """
    Check payment status and update subscription.
    
    Call this after returning from Stripe checkout.
    """
    from services.payment_service import payment_service
    
    result = await payment_service.check_payment_status(
        session_id=request_data.session_id,
        origin_url=request_data.origin_url
    )
    return result


@router.post("/reactivate")
async def reactivate_subscription(user: User = Depends(require_owner)):
    """Re-process the most recent paid subscription transaction if the company
    subscription is not yet active. Handles cases where payment succeeded but
    activation was skipped (e.g. email failure on first attempt)."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    from services.payment_service import payment_service

    company = await db.companies.find_one(
        {"company_id": user.company_id}, {"_id": 0, "subscription_active": 1}
    ) or {}
    if company.get("subscription_active"):
        return {"status": "already_active"}

    txn = await db.payment_transactions.find_one(
        {"company_id": user.company_id, "type": "subscription", "payment_status": "paid"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    if not txn:
        return {"status": "no_paid_transaction"}

    await payment_service._process_successful_payment(txn)
    return {"status": "activated", "plan_id": txn.get("plan_id")}


@router.get("/transactions")
async def get_transactions(
    limit: int = 20,
    user: User = Depends(require_owner)
):
    """
    Get payment transaction history.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    transactions = await db.payment_transactions.find(
        {"company_id": user.company_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"transactions": transactions, "total": len(transactions)}


@router.post("/checkout/payslip")
async def create_payslip_checkout(
    request_data: PayslipCheckoutRequest,
    user: User = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for a single £5 payslip download.
    
    payslip_id format accepted:
      - "{payrun_id}:{employee_id}"  (manager/admin downloading a specific employee)
      - "{payrun_id}"                 (self-service: resolves employee from current user)
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    raw = request_data.payslip_id or ""
    if ":" in raw:
        payrun_id, employee_id = raw.split(":", 1)
    else:
        payrun_id = raw
        # Self-service: resolve employee by user's email
        emp = await db.employees.find_one({"email": user.email, "company_id": user.company_id}, {"_id": 0})
        if not emp:
            raise HTTPException(status_code=404, detail="Employee record not found")
        employee_id = emp["employee_id"]

    payslip = await db.payslips.find_one(
        {"payrun_id": payrun_id, "employee_id": employee_id},
        {"_id": 0}
    )
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    payrun = await db.pay_runs.find_one({"payrun_id": payrun_id}, {"_id": 0})
    if not payrun or payrun.get("company_id") != user.company_id:
        raise HTTPException(status_code=403, detail="Not your payslip")

    canonical_id = f"{payrun_id}:{employee_id}"

    # Block during trial — no downloads allowed
    from services.trial_service import trial_service
    status = await trial_service.get_trial_status(user.company_id)
    if status.get("trial_active"):
        raise HTTPException(
            status_code=403,
            detail="Downloads are disabled during the free trial. Upgrade your plan to enable payslip downloads."
        )

    from services.payment_service import payment_service
    try:
        return await payment_service.create_payslip_download_checkout(
            payslip_id=canonical_id,
            payrun_id=payrun_id,
            company_id=user.company_id,
            user_id=user.user_id,
            user_email=user.email,
            origin_url=request_data.origin_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/{transaction_id}/receipt")
async def get_transaction_receipt(
    transaction_id: str,
    user: User = Depends(get_current_user)
):
    """Return Stripe receipt URL for a paid transaction owned by this company."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    tx = await db.payment_transactions.find_one(
        {"transaction_id": transaction_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Transaction not paid yet")
    if tx.get("receipt_url"):
        return {"receipt_url": tx["receipt_url"]}

    # Lazy fetch receipt from Stripe if missing
    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
        if tx.get("session_id"):
            session = stripe.checkout.Session.retrieve(
                tx["session_id"], expand=["payment_intent.latest_charge"]
            )
            charge = ((session.get("payment_intent") or {}).get("latest_charge")) if isinstance(session.get("payment_intent"), dict) else None
            url = (charge or {}).get("receipt_url") if isinstance(charge, dict) else None
            if url:
                await db.payment_transactions.update_one(
                    {"transaction_id": transaction_id},
                    {"$set": {"receipt_url": url}}
                )
                return {"receipt_url": url}
    except Exception as exc:
        logger.error(f"Stripe receipt fetch failed: {exc}")
    raise HTTPException(status_code=404, detail="Receipt not available")


@router.get("/usage/this-month")
async def get_download_usage(user: User = Depends(get_current_user)):
    """Return how many of the plan's free downloads have been used this month + bulk-pass status."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.trial_service import TrialService
    from services.payment_service import PLAN_DOWNLOAD_QUOTA
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    status = await TrialService.get_trial_status(user.company_id)
    plan_id = status.get("plan_id")
    quota = PLAN_DOWNLOAD_QUOTA.get(plan_id, 0)

    usage = await db.download_usage.find_one(
        {"company_id": user.company_id, "month": month_key}, {"_id": 0}
    ) or {"count": 0}

    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0}) or {}
    bulk_active = False
    bulk_until = company.get("bulk_downloads_active_until")
    if bulk_until:
        try:
            bulk_dt = datetime.fromisoformat(bulk_until.replace("Z", "+00:00"))
            bulk_active = bulk_dt > now
        except (ValueError, TypeError):
            bulk_active = False

    return {
        "month": month_key,
        "plan_id": plan_id,
        "quota": quota,  # -1 = unlimited, 0 = no plan
        "used_this_month": usage.get("count", 0),
        "remaining": (-1 if quota == -1 else max(0, quota - usage.get("count", 0))),
        "bulk_downloads_active": bulk_active,
        "bulk_downloads_until": bulk_until if bulk_active else None,
        "price_per_download": 5.00,
        "bulk_offer_price": 29.00,
        "bulk_offer_id": "bulk_downloads_monthly",
    }


@router.post("/portal")
async def create_billing_portal(
    data: dict,
    user: User = Depends(require_owner),
):
    """
    Create a Stripe Customer Portal session so the customer can self-serve
    payment methods, cancel subscription, download invoices.
    
    Body: { "return_url": "https://app.example.com/billing" }
    """
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    return_url = data.get("return_url") or f"{os.environ.get('APP_URL', 'https://realtouchhr.com')}/billing"
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    # Find a completed transaction to get the Stripe customer id
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    stripe_customer_id = (company or {}).get("stripe_customer_id")

    if not stripe_customer_id:
        # Try to extract customer id from the most recent paid transaction
        tx = await db.payment_transactions.find_one(
            {"company_id": user.company_id, "payment_status": "paid"},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
        if tx and tx.get("session_id"):
            try:
                session = stripe.checkout.Session.retrieve(tx["session_id"])
                stripe_customer_id = session.get("customer")
                if stripe_customer_id:
                    await db.companies.update_one(
                        {"company_id": user.company_id},
                        {"$set": {"stripe_customer_id": stripe_customer_id}}
                    )
            except Exception as exc:
                logger.error(f"Could not resolve Stripe customer: {exc}")

    if not stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer found. Complete a subscription checkout first."
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return {"portal_url": portal_session.url, "customer_id": stripe_customer_id}
    except Exception as exc:
        logger.error(f"Stripe portal creation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Portal session failed: {exc}")


# ==================== WEBHOOK ROUTE ====================

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    """
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    
    # Get origin from request
    origin_url = str(request.base_url).rstrip("/")
    
    from services.payment_service import payment_service
    
    try:
        result = await payment_service.handle_webhook(
            request_body=body,
            signature=signature,
            origin_url=origin_url
        )
        return result
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
