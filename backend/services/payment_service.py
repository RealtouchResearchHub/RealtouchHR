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

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

logger = logging.getLogger(__name__)


# ==================== SUBSCRIPTION PLANS ====================

class SubscriptionPlan(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Fixed pricing packages (server-side only - never accept amounts from frontend)
SUBSCRIPTION_PLANS = {
    "starter": {
        "name": "Starter",
        "price": 49.00,  # Monthly in GBP
        "currency": "gbp",
        "features": [
            "Up to 10 employees",
            "Basic HR features",
            "Payroll processing",
            "Email support"
        ],
        "employee_limit": 10
    },
    "professional": {
        "name": "Professional",
        "price": 149.00,
        "currency": "gbp",
        "features": [
            "Up to 50 employees",
            "Full HR suite",
            "Payroll + RTI submissions",
            "UKVI compliance",
            "Priority support"
        ],
        "employee_limit": 50
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 399.00,
        "currency": "gbp",
        "features": [
            "Unlimited employees",
            "All features included",
            "Multi-entity support",
            "SCIM/SAML SSO",
            "Dedicated support",
            "Custom integrations"
        ],
        "employee_limit": -1  # Unlimited
    }
}

# One-time add-ons
ADDONS = {
    "extra_users_10": {
        "name": "Extra 10 Users",
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
        """
        Create a Stripe checkout session for a subscription plan.
        
        Amount is determined server-side from SUBSCRIPTION_PLANS.
        """
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_id}")
        
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        # Import Stripe checkout
        from emergentintegrations.payments.stripe.checkout import (
            StripeCheckout, 
            CheckoutSessionRequest
        )
        
        # Build URLs from origin
        success_url = f"{origin_url}/settings/billing?session_id={{CHECKOUT_SESSION_ID}}&status=success"
        cancel_url = f"{origin_url}/settings/billing?status=cancelled"
        webhook_url = f"{origin_url}/api/webhook/stripe"
        
        # Initialize Stripe checkout
        stripe_checkout = StripeCheckout(
            api_key=self.stripe_api_key,
            webhook_url=webhook_url
        )
        
        # Create checkout request
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
                "type": "subscription"
            }
        )
        
        # Create Stripe checkout session
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
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
            "payment_status": "pending",
            "status": "initiated",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.payment_transactions.insert_one(transaction)
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "plan": plan
        }
    
    async def create_payslip_download_checkout(
        self,
        payslip_id: str,
        payrun_id: str,
        company_id: str,
        user_id: str,
        user_email: str,
        origin_url: str
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for a single £5 payslip download.
        Amount is server-enforced.
        """
        from services.trial_service import PAYSLIP_DOWNLOAD_PRICE, PAYSLIP_DOWNLOAD_CURRENCY
        from emergentintegrations.payments.stripe.checkout import (
            StripeCheckout,
            CheckoutSessionRequest
        )

        success_url = f"{origin_url}/payroll?session_id={{CHECKOUT_SESSION_ID}}&status=success&payslip_id={payslip_id}"
        cancel_url = f"{origin_url}/payroll?status=cancelled"
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
        
        from emergentintegrations.payments.stripe.checkout import (
            StripeCheckout, 
            CheckoutSessionRequest
        )
        
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
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        
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
        
        # Check if already processed
        if transaction.get("payment_status") == "paid":
            return {
                "status": transaction.get("status"),
                "payment_status": "paid",
                "already_processed": True,
                "session_id": session_id
            }
        
        # Update transaction
        new_status = "completed" if status_response.payment_status == "paid" else status_response.status
        new_payment_status = status_response.payment_status
        
        # Capture Stripe customer id for future billing-portal access
        customer_id = getattr(status_response, "customer_id", None) or getattr(status_response, "customer", None)
        update_fields = {
            "status": new_status,
            "payment_status": new_payment_status,
            "amount_total": status_response.amount_total,
            "updated_at": now.isoformat()
        }
        if customer_id:
            update_fields["stripe_customer_id"] = customer_id
        
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": update_fields}
        )

        # Mirror customer id to company for billing portal
        if customer_id and transaction.get("company_id"):
            await db.companies.update_one(
                {"company_id": transaction["company_id"]},
                {"$set": {"stripe_customer_id": customer_id}}
            )
        
        # If payment successful, update company subscription
        if new_payment_status == "paid":
            await self._process_successful_payment(transaction)
        
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
            
            # Update company subscription
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": {
                    "subscription_plan": plan_id,
                    "subscription_name": plan.get("name"),
                    "employee_limit": plan.get("employee_limit", 10),
                    "subscription_updated_at": now.isoformat(),
                    "subscription_active": True
                }}
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
            
            # Send notification email
            from services.email_service import email_service
            await email_service.send_subscription_confirmation(
                to_email=transaction.get("user_email"),
                plan_name=plan.get("name"),
                amount=transaction.get("amount"),
                currency=transaction.get("currency")
            )

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

        elif payment_type == "addon":
            addon_id = transaction.get("addon_id")
            quantity = transaction.get("quantity", 1)
            
            if addon_id == "extra_users_10":
                # Increase employee limit
                await db.companies.update_one(
                    {"company_id": company_id},
                    {"$inc": {"employee_limit": 10 * quantity}}
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
        """Handle Stripe webhook events"""
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        
        webhook_url = f"{origin_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(
            api_key=self.stripe_api_key,
            webhook_url=webhook_url
        )
        
        webhook_response = await stripe_checkout.handle_webhook(
            request_body,
            signature
        )
        
        # Process based on event type
        if webhook_response.payment_status == "paid":
            await self.check_payment_status(webhook_response.session_id, origin_url)
        
        return {
            "event_type": webhook_response.event_type,
            "event_id": webhook_response.event_id,
            "session_id": webhook_response.session_id,
            "payment_status": webhook_response.payment_status
        }
    
    async def get_company_billing(self, company_id: str) -> Dict[str, Any]:
        """Get company billing information and transaction history"""
        company = await db.companies.find_one(
            {"company_id": company_id},
            {"_id": 0, "subscription_plan": 1, "subscription_name": 1, 
             "employee_limit": 1, "subscription_active": 1, "subscription_updated_at": 1}
        )
        
        transactions = await db.payment_transactions.find(
            {"company_id": company_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
        
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
