"""
RealtouchHR - Payment Service (Stripe Integration)
SaaS Subscription Billing for RealtouchHR Platform

Features:
- Subscription plans (Starter, Professional, Enterprise)
- One-time payments
- Payment status tracking
- Webhook handling
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import uuid

from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
logger = logging.getLogger(__name__)

import stripe as _stripe_sdk

# Stripe Price IDs for recurring subscription plans (set in .env)
# When set, checkout uses mode="subscription" with the pre-created Stripe price.
# When missing, falls back to ad-hoc price_data with recurring interval.
STRIPE_PRICE_IDS = {
    "starter":      os.environ.get("STRIPE_PRICE_STARTER", ""),
    "professional": os.environ.get("STRIPE_PRICE_PROFESSIONAL", ""),
    "enterprise":   os.environ.get("STRIPE_PRICE_ENTERPRISE", ""),
}


# ==================== STRIPE HELPERS ====================

class CheckoutSessionRequest:
    def __init__(self, amount, currency, success_url, cancel_url,
                 metadata=None, price_id=None, mode="payment", product_name=None):
        self.amount = amount
        self.currency = currency
        self.success_url = success_url
        self.cancel_url = cancel_url
        self.metadata = metadata or {}
        self.price_id = price_id        # Stripe Price ID; triggers subscription mode
        self.mode = mode                # "payment" | "subscription"
        self.product_name = product_name or "RealtouchHR Payment"


class _CheckoutResult:
    def __init__(self, session):
        self.session_id = session.id
        self.url = getattr(session, "url", None)
        # Subscription mode: payment_status is None; derive from session status
        raw_ps = getattr(session, "payment_status", None)
        sess_status = getattr(session, "status", None)
        self.payment_status = raw_ps if raw_ps else ("paid" if sess_status == "complete" else "unpaid")
        self.status = sess_status
        self.amount_total = getattr(session, "amount_total", None)
        self.currency = getattr(session, "currency", None)
        self.customer_id = session.get("customer") if hasattr(session, "get") else getattr(session, "customer", None)
        self.customer = self.customer_id
        self.subscription_id = session.get("subscription") if hasattr(session, "get") else getattr(session, "subscription", None)


class StripeCheckout:
    def __init__(self, api_key, webhook_url=None):
        self.api_key = api_key

    async def create_checkout_session(self, request: CheckoutSessionRequest) -> _CheckoutResult:
        _stripe_sdk.api_key = self.api_key
        if request.price_id and request.mode == "subscription":
            # Pre-created Stripe recurring price
            session = _stripe_sdk.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": request.price_id, "quantity": 1}],
                mode="subscription",
                allow_promotion_codes=True,
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata,
            )
        elif request.mode == "subscription":
            # Subscription mode with ad-hoc price_data (no pre-created Price ID yet)
            session = _stripe_sdk.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": request.currency,
                        "product_data": {"name": request.product_name},
                        "unit_amount": int(request.amount * 100),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                allow_promotion_codes=True,
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata,
            )
        else:
            # One-time payment (payslip downloads, add-ons)
            session = _stripe_sdk.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": request.currency,
                        "product_data": {"name": request.product_name},
                        "unit_amount": int(request.amount * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata,
            )
        return _CheckoutResult(session)

    async def get_checkout_status(self, session_id: str) -> _CheckoutResult:
        _stripe_sdk.api_key = self.api_key
        session = _stripe_sdk.checkout.Session.retrieve(session_id)
        return _CheckoutResult(session)


# ==================== SUBSCRIPTION PLANS ====================

class SubscriptionPlan(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Fixed pricing packages (server-side only - never accept amounts from frontend)
# Pricing per PDF spec: Starter £29, Professional £39, Enterprise £129
SUBSCRIPTION_PLANS = {
    "starter": {
        "name": "Starter",
        "price": 29.00,
        "currency": "gbp",
        "features": [
            "Up to 10 employees",
            "Core HR features",
            "Payroll processing",
            "2 UKVI compliance scans/month",
            "Payslip preview (free)",
            "Email support"
        ],
        "employee_limit": 10,
        "feature_keys": [
            "payroll_processing",
            "payslip_preview",
            "payslip_paid_download",
            "ukvi_compliance_scanner",
            "leave_management",
            "document_management"
        ]
    },
    "professional": {
        "name": "Professional",
        "price": 39.00,
        "currency": "gbp",
        "features": [
            "Up to 50 employees",
            "Full HR suite",
            "Payroll + HMRC RTI submissions",
            "2 UKVI compliance scans/month",
            "UKVI compliance report downloads",
            "Payslip preview (free)",
            "Priority support"
        ],
        "employee_limit": 50,
        "feature_keys": [
            "payroll_processing",
            "hmrc_rti",
            "payslip_preview",
            "payslip_paid_download",
            "ukvi_compliance_scanner",
            "ukvi_report_download",
            "leave_management",
            "document_management",
            "hr_analytics",
            "performance_management"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 129.00,
        "currency": "gbp",
        "features": [
            "Unlimited employees",
            "All features included",
            "Multi-entity support",
            "SCIM/SAML SSO",
            "2 UKVI compliance scans/month",
            "UKVI compliance report downloads",
            "Dedicated account manager",
            "Custom integrations"
        ],
        "employee_limit": -1,
        "feature_keys": [
            "payroll_processing",
            "hmrc_rti",
            "payslip_preview",
            "payslip_paid_download",
            "ukvi_compliance_scanner",
            "ukvi_report_download",
            "enterprise_multi_entity",
            "enterprise_sso",
            "leave_management",
            "document_management",
            "hr_analytics",
            "performance_management",
            "advanced_reporting"
        ]
    }
}

# UKVI Compliance Scanner: 2 scans per billing month across all plans
UKVI_SCAN_QUOTA_PER_MONTH = 2

# One-time add-ons
ADDONS = {
    "extra_users_10": {
        "name": "Extra 10 Employees",
        "price": 25.00,
        "currency": "gbp"
    },
    "priority_support": {
        "name": "Priority Support Add-on",
        "price": 99.00,
        "currency": "gbp"
    },
    "data_migration": {
        "name": "Data Migration Service",
        "price": 299.00,
        "currency": "gbp"
    }
}

# Payslip downloads: preview free, PDF download is £5 per payslip (all plans)
# No free monthly quota — all payslip PDF downloads are pay-per-download
PLAN_DOWNLOAD_QUOTA = {
    "starter": 0,
    "professional": 0,
    "enterprise": 0,
}


# ==================== PAYMENT SERVICE ====================

class PaymentService:
    """Service for Stripe payment integration"""
    
    def __init__(self):
        self.stripe_api_key = os.environ.get('STRIPE_API_KEY')
    
    async def create_subscription_checkout(
        self,
        plan_id: str,
        company_id: str,
        user_id: str,
        user_email: str,
        origin_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session for a subscription plan.
        Uses a pre-created Stripe Price ID when configured (STRIPE_PRICE_*),
        otherwise falls back to ad-hoc price_data with monthly recurrence."""
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")

        plan = SUBSCRIPTION_PLANS[plan_id]
        price_id = STRIPE_PRICE_IDS.get(plan_id, "")

        success_url = f"{origin_url}/settings/billing?session_id={{CHECKOUT_SESSION_ID}}&status=success"
        cancel_url = f"{origin_url}/settings/billing?status=cancelled"

        stripe_checkout = StripeCheckout(api_key=self.stripe_api_key)

        checkout_request = CheckoutSessionRequest(
            amount=plan["price"],
            currency=plan["currency"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "company_id": company_id,
                "user_id": user_id,
                "user_email": user_email,
                "plan_id": plan_id,
                "plan_name": plan["name"],
                "type": "subscription",
            },
            price_id=price_id or None,
            mode="subscription",
            product_name=f"RealtouchHR {plan['name']} Plan",
        )

        session = await stripe_checkout.create_checkout_session(checkout_request)

        now = datetime.now(timezone.utc)
        transaction = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "session_id": session.session_id,
            "company_id": company_id,
            "user_id": user_id,
            "user_email": user_email,
            "type": "subscription",
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "amount": plan["price"],
            "currency": plan["currency"],
            "stripe_price_id": price_id or None,
            "checkout_mode": "subscription",
            "payment_status": "pending",
            "status": "initiated",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.payment_transactions.insert_one(transaction)

        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "plan": plan,
            "mode": "subscription",
            "price_id_used": bool(price_id),
        }
    
    async def create_payslip_download_checkout(
        self,
        payslip_id: str,
        payrun_id: str,
        company_id: str,
        user_id: str,
        user_email: str,
        origin_url: str,
        return_path: str = "/payroll"
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for a single £5 payslip download.
        Amount is server-enforced.

        return_path is the page the user initiated the download from (e.g.
        "/payroll/<id>" for admins, "/self-service" for employees) so Stripe
        redirects back to a page that actually has a download-resume handler
        and that the user's role is allowed to visit.
        """
        from services.trial_service import PAYSLIP_DOWNLOAD_PRICE, PAYSLIP_DOWNLOAD_CURRENCY
        if not return_path.startswith("/") or return_path.startswith("//"):
            return_path = "/payroll"
        success_url = f"{origin_url}{return_path}?session_id={{CHECKOUT_SESSION_ID}}&status=success&payslip_id={payslip_id}"
        cancel_url = f"{origin_url}{return_path}?status=cancelled"
        webhook_url = f"{origin_url}/api/webhook/stripe"

        stripe_checkout = StripeCheckout(
            api_key=self.stripe_api_key,
            webhook_url=webhook_url
        )

        checkout_request = CheckoutSessionRequest(
            amount=PAYSLIP_DOWNLOAD_PRICE,
            currency=PAYSLIP_DOWNLOAD_CURRENCY,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "company_id": company_id,
                "user_id": user_id,
                "user_email": user_email,
                "payslip_id": payslip_id,
                "payrun_id": payrun_id,
                "type": "payslip_download"
            }
        )

        session = await stripe_checkout.create_checkout_session(checkout_request)

        now = datetime.now(timezone.utc)
        transaction = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "session_id": session.session_id,
            "company_id": company_id,
            "user_id": user_id,
            "user_email": user_email,
            "type": "payslip_download",
            "payslip_id": payslip_id,
            "payrun_id": payrun_id,
            "amount": PAYSLIP_DOWNLOAD_PRICE,
            "currency": PAYSLIP_DOWNLOAD_CURRENCY,
            "payment_status": "pending",
            "status": "initiated",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.payment_transactions.insert_one(transaction)

        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "amount": PAYSLIP_DOWNLOAD_PRICE,
            "currency": PAYSLIP_DOWNLOAD_CURRENCY
        }

    async def create_addon_checkout(
        self,
        addon_id: str,
        company_id: str,
        user_id: str,
        user_email: str,
        origin_url: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Create checkout for one-time add-on purchase"""
        if addon_id not in ADDONS:
            raise ValueError(f"Invalid addon: {addon_id}")
        
        addon = ADDONS[addon_id]
        total_amount = addon["price"] * quantity
        
        success_url = f"{origin_url}/settings/billing?session_id={{CHECKOUT_SESSION_ID}}&status=success"
        cancel_url = f"{origin_url}/settings/billing?status=cancelled"
        webhook_url = f"{origin_url}/api/webhook/stripe"

        stripe_checkout = StripeCheckout(
            api_key=self.stripe_api_key,
            webhook_url=webhook_url
        )

        checkout_request = CheckoutSessionRequest(
            amount=total_amount,
            currency=addon["currency"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "company_id": company_id,
                "user_id": user_id,
                "user_email": user_email,
                "addon_id": addon_id,
                "addon_name": addon["name"],
                "quantity": str(quantity),
                "type": "addon"
            }
        )
        
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        now = datetime.now(timezone.utc)
        transaction = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "session_id": session.session_id,
            "company_id": company_id,
            "user_id": user_id,
            "user_email": user_email,
            "type": "addon",
            "addon_id": addon_id,
            "addon_name": addon["name"],
            "quantity": quantity,
            "amount": total_amount,
            "currency": addon["currency"],
            "payment_status": "pending",
            "status": "initiated",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.payment_transactions.insert_one(transaction)
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "addon": addon,
            "quantity": quantity,
            "total_amount": total_amount
        }
    
    async def check_payment_status(
        self,
        session_id: str,
        origin_url: str
    ) -> Dict[str, Any]:
        """Check payment status and update database"""
        webhook_url = f"{origin_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(
            api_key=self.stripe_api_key,
            webhook_url=webhook_url
        )
        
        # Get status from Stripe
        status_response = await stripe_checkout.get_checkout_status(session_id)
        
        now = datetime.now(timezone.utc)
        
        # Find and update transaction
        transaction = await db.payment_transactions.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        
        if not transaction:
            return {
                "error": "Transaction not found",
                "session_id": session_id
            }
        
        # Check if already processed — but still ensure subscription is active
        # (it may have been skipped if e.g. the email step failed on first attempt)
        if transaction.get("payment_status") == "paid":
            if transaction.get("type") == "subscription" and transaction.get("company_id"):
                company = await db.companies.find_one(
                    {"company_id": transaction["company_id"]}, {"_id": 0, "subscription_active": 1}
                ) or {}
                if not company.get("subscription_active"):
                    await self._process_successful_payment(transaction)
            return {
                "status": transaction.get("status"),
                "payment_status": "paid",
                "already_processed": True,
                "session_id": session_id
            }
        
        # Update transaction
        new_status = "completed" if status_response.payment_status == "paid" else status_response.status
        new_payment_status = status_response.payment_status
        
        # Capture Stripe customer id + receipt URL via direct stripe SDK
        customer_id = getattr(status_response, "customer_id", None) or getattr(status_response, "customer", None)
        receipt_url = None
        payment_intent_id = None
        try:
            import stripe
            stripe.api_key = self.stripe_api_key
            session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent.latest_charge"])
            customer_id = customer_id or session.get("customer")
            payment_intent_id = (session.get("payment_intent") or {}).get("id") if isinstance(session.get("payment_intent"), dict) else session.get("payment_intent")
            charge = ((session.get("payment_intent") or {}).get("latest_charge")) if isinstance(session.get("payment_intent"), dict) else None
            if charge and isinstance(charge, dict):
                receipt_url = charge.get("receipt_url")
        except Exception as exc:
            logger.warning(f"Could not fetch Stripe receipt: {exc}")

        # Also capture subscription_id (set for subscription mode sessions)
        subscription_id = getattr(status_response, "subscription_id", None)

        update_fields = {
            "status": new_status,
            "payment_status": new_payment_status,
            "amount_total": status_response.amount_total,
            "updated_at": now.isoformat()
        }
        if customer_id:
            update_fields["stripe_customer_id"] = customer_id
        if receipt_url:
            update_fields["receipt_url"] = receipt_url
        if payment_intent_id:
            update_fields["payment_intent_id"] = payment_intent_id
        if subscription_id:
            update_fields["stripe_subscription_id"] = subscription_id

        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": update_fields}
        )

        # Mirror customer id and subscription id to company
        if transaction.get("company_id"):
            company_update = {}
            if customer_id:
                company_update["stripe_customer_id"] = customer_id
            if subscription_id:
                company_update["stripe_subscription_id"] = subscription_id
            if company_update:
                await db.companies.update_one(
                    {"company_id": transaction["company_id"]},
                    {"$set": company_update}
                )

        # If payment successful, activate subscription
        if new_payment_status == "paid":
            merged_txn = {**transaction, **update_fields}
            await self._process_successful_payment(merged_txn)

        return {
            "status": new_status,
            "payment_status": new_payment_status,
            "amount_total": status_response.amount_total,
            "currency": status_response.currency,
            "session_id": session_id
        }

    async def _process_successful_payment(self, transaction: dict):
        """Process successful payment - update subscription, send notifications"""
        company_id = transaction.get("company_id")
        payment_type = transaction.get("type")
        now = datetime.now(timezone.utc)

        if payment_type == "subscription":
            plan_id = transaction.get("plan_id")
            plan = SUBSCRIPTION_PLANS.get(plan_id, {})

            company_update = {
                "subscription_plan": plan_id,
                "subscription_name": plan.get("name"),
                "employee_limit": plan.get("employee_limit", 10),
                "subscription_updated_at": now.isoformat(),
                "subscription_active": True,
            }
            if transaction.get("stripe_subscription_id"):
                company_update["stripe_subscription_id"] = transaction["stripe_subscription_id"]

            # Update company subscription
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": company_update}
            )
            
            # Create audit log
            await db.audit_log.insert_one({
                "action": "subscription_activated",
                "entity_type": "company",
                "entity_id": company_id,
                "details": {
                    "plan_id": plan_id,
                    "amount": transaction.get("amount"),
                    "transaction_id": transaction.get("transaction_id")
                },
                "timestamp": now.isoformat()
            })
            
            # Send notification email — non-fatal: never let this block activation
            try:
                from services.email_service import email_service
                await email_service.send_subscription_confirmation(
                    to_email=transaction.get("user_email"),
                    plan_name=plan.get("name"),
                    amount=transaction.get("amount"),
                    currency=transaction.get("currency")
                )
            except Exception as email_exc:
                logger.warning("Subscription confirmation email failed (non-fatal): %s", email_exc)

        elif payment_type == "payslip_download":
            # Issue a one-use download pass valid for 30 min
            from services.trial_service import download_gate
            pass_data = await download_gate.issue_pass(
                company_id=company_id,
                user_id=transaction.get("user_id"),
                resource_id=transaction.get("payslip_id"),
                resource_type="payslip",
                transaction_id=transaction.get("transaction_id"),
            )
            await db.audit_log.insert_one({
                "action": "payslip_download_paid",
                "entity_type": "payslip",
                "entity_id": transaction.get("payslip_id"),
                "details": {
                    "amount": transaction.get("amount"),
                    "user_id": transaction.get("user_id"),
                    "pass_id": pass_data["pass_id"],
                },
                "timestamp": now.isoformat()
            })

            # Send payment receipt email — non-fatal: never let this block the download pass
            try:
                from services.email_service import email_service
                await email_service.send_payslip_payment_confirmation(
                    to_email=transaction.get("user_email"),
                    amount=transaction.get("amount"),
                    currency=transaction.get("currency", "gbp"),
                )
            except Exception as email_exc:
                logger.warning("Payslip payment confirmation email failed (non-fatal): %s", email_exc)

        elif payment_type == "addon":
            addon_id = transaction.get("addon_id")
            quantity = transaction.get("quantity", 1)
            
            if addon_id == "extra_users_10":
                # Increase employee limit
                await db.companies.update_one(
                    {"company_id": company_id},
                    {"$inc": {"employee_limit": 10 * quantity}}
                )
            elif addon_id == "bulk_downloads_monthly":
                # Activate 30-day unlimited downloads
                duration_days = ADDONS["bulk_downloads_monthly"].get("duration_days", 30)
                # Stack: extend existing window if active, else start fresh
                existing = await db.companies.find_one(
                    {"company_id": company_id},
                    {"_id": 0, "bulk_downloads_active_until": 1}
                ) or {}
                start_from = now
                existing_until = existing.get("bulk_downloads_active_until")
                if existing_until:
                    try:
                        existing_dt = datetime.fromisoformat(existing_until.replace("Z", "+00:00"))
                        if existing_dt > now:
                            start_from = existing_dt
                    except (ValueError, TypeError):
                        pass
                new_until = start_from + timedelta(days=duration_days)
                await db.companies.update_one(
                    {"company_id": company_id},
                    {"$set": {"bulk_downloads_active_until": new_until.isoformat()}}
                )
            
            # Create audit log
            await db.audit_log.insert_one({
                "action": "addon_purchased",
                "entity_type": "company",
                "entity_id": company_id,
                "details": {
                    "addon_id": addon_id,
                    "quantity": quantity,
                    "amount": transaction.get("amount"),
                    "transaction_id": transaction.get("transaction_id")
                },
                "timestamp": now.isoformat()
            })
    
    async def handle_webhook(
        self,
        request_body: bytes,
        signature: str,
        origin_url: str
    ) -> Dict[str, Any]:
        """Handle all Stripe webhook events — checkout, subscription lifecycle, renewals."""
        _stripe_sdk.api_key = self.stripe_api_key
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        try:
            event = _stripe_sdk.Webhook.construct_event(request_body, signature, webhook_secret)
        except Exception as exc:
            raise ValueError(f"Invalid webhook signature: {exc}")

        event_type = event.type
        obj = event.data.object

        # ── Checkout completed (both payment and subscription modes) ──────────
        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            session_id = obj.id
            raw_ps = obj.get("payment_status")
            is_paid = raw_ps == "paid" or (not raw_ps and obj.get("status") == "complete")
            if is_paid:
                try:
                    await self.check_payment_status(session_id, origin_url)
                except Exception as exc:
                    logger.warning("Webhook check_payment_status failed for %s: %s", session_id, exc)
            return {"event_type": event_type, "event_id": event.id, "session_id": session_id}

        if event_type == "checkout.session.async_payment_failed":
            session_id = obj.id
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "failed", "status": "failed",
                          "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"event_type": event_type, "event_id": event.id, "session_id": session_id}

        # ── Recurring invoice paid (subscription renewal) ─────────────────────
        if event_type == "invoice.paid":
            try:
                await self._handle_invoice_paid(obj)
            except Exception as exc:
                logger.warning("invoice.paid handling failed: %s", exc)
            return {"event_type": event_type, "event_id": event.id}

        # ── Subscription lifecycle ─────────────────────────────────────────────
        if event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
            try:
                await self._handle_subscription_event(event_type, obj)
            except Exception as exc:
                logger.warning("%s handling failed: %s", event_type, exc)
            return {"event_type": event_type, "event_id": event.id}

        return {"event_type": event_type, "event_id": event.id, "skipped": True}

    async def _handle_invoice_paid(self, invoice: dict):
        """Keep subscription active on monthly renewal."""
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")
        if not customer_id:
            return
        company = await db.companies.find_one({"stripe_customer_id": customer_id}, {"_id": 0}) or {}
        if not company:
            logger.warning("invoice.paid: no company for customer %s", customer_id)
            return
        company_id = company.get("company_id")
        now = datetime.now(timezone.utc)
        update = {"subscription_active": True, "subscription_renewed_at": now.isoformat()}
        if subscription_id:
            update["stripe_subscription_id"] = subscription_id
        await db.companies.update_one({"company_id": company_id}, {"$set": update})
        await db.audit_log.insert_one({
            "action": "subscription_renewed",
            "entity_type": "company",
            "entity_id": company_id,
            "details": {"subscription_id": subscription_id, "invoice_id": invoice.get("id")},
            "timestamp": now.isoformat(),
        })

    async def _handle_subscription_event(self, event_type: str, subscription: dict):
        """Handle subscription updated/deleted — activate or deactivate accordingly."""
        customer_id = subscription.get("customer")
        subscription_id = subscription.get("id")
        status = subscription.get("status")
        if not customer_id:
            return
        company = await db.companies.find_one({"stripe_customer_id": customer_id}, {"_id": 0}) or {}
        if not company:
            logger.warning("%s: no company for customer %s", event_type, customer_id)
            return
        company_id = company.get("company_id")
        now = datetime.now(timezone.utc)
        if event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid"):
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": {
                    "subscription_active": False,
                    "subscription_cancelled_at": now.isoformat(),
                    "stripe_subscription_id": subscription_id,
                }}
            )
            await db.audit_log.insert_one({
                "action": "subscription_cancelled",
                "entity_type": "company",
                "entity_id": company_id,
                "details": {"subscription_id": subscription_id, "status": status},
                "timestamp": now.isoformat(),
            })
        elif status == "active":
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": {"subscription_active": True, "stripe_subscription_id": subscription_id}}
            )
    
    async def get_company_billing(self, company_id: str) -> Dict[str, Any]:
        """Get company billing information and transaction history"""
        try:
            company = await db.companies.find_one(
                {"company_id": company_id},
                {"_id": 0, "subscription_plan": 1, "subscription_name": 1,
                 "employee_limit": 1, "subscription_active": 1, "subscription_updated_at": 1}
            )
        except Exception:
            company = None

        try:
            transactions = await db.payment_transactions.find(
                {"company_id": company_id},
                {"_id": 0}
            ).sort("created_at", -1).limit(20).to_list(20)
        except Exception:
            transactions = []

        current_plan = None
        if company and company.get("subscription_plan"):
            plan_id = company.get("subscription_plan")
            current_plan = {
                "id": plan_id,
                **SUBSCRIPTION_PLANS.get(plan_id, {})
            }

        return {
            "company_id": company_id,
            "current_plan": current_plan,
            "subscription_active": company.get("subscription_active", False) if company else False,
            "employee_limit": company.get("employee_limit", 10) if company else 10,
            "transactions": transactions,
            "available_plans": SUBSCRIPTION_PLANS,
            "available_addons": ADDONS
        }


# Singleton instance
payment_service = PaymentService()
