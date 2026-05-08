"""
Trial & Pay-per-Download Service
- 7-day free trial (no downloads)
- £5 per payslip download for paying customers
- Creates Stripe checkout sessions for micro-payments
- Issues short-lived download passes on successful payment
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
logger = logging.getLogger(__name__)

# Trial settings
TRIAL_DURATION_DAYS = 7
PAYSLIP_DOWNLOAD_PRICE = 5.00  # GBP — immutable on backend
PAYSLIP_DOWNLOAD_CURRENCY = "gbp"
DOWNLOAD_PASS_VALIDITY_MINUTES = 30


class TrialService:

    @staticmethod
    async def start_trial(company_id: str) -> Dict[str, Any]:
        """Start a 7-day free trial for a company. Idempotent."""
        now = datetime.now(timezone.utc)
        company = await db.companies.find_one({"company_id": company_id}, {"_id": 0})
        if not company:
            return {"started": False, "reason": "Company not found"}
        if company.get("trial_started_at"):
            # Already had a trial
            return {
                "started": False,
                "reason": "Trial already used",
                "trial_ends_at": company.get("trial_ends_at"),
            }
        trial_ends = now + timedelta(days=TRIAL_DURATION_DAYS)
        await db.companies.update_one(
            {"company_id": company_id},
            {"$set": {
                "trial_active": True,
                "trial_started_at": now.isoformat(),
                "trial_ends_at": trial_ends.isoformat(),
            }}
        )
        return {"started": True, "trial_ends_at": trial_ends.isoformat()}

    @staticmethod
    async def get_trial_status(company_id: str) -> Dict[str, Any]:
        """Return trial + subscription status"""
        company = await db.companies.find_one({"company_id": company_id}, {"_id": 0}) or {}
        now = datetime.now(timezone.utc)

        trial_active = bool(company.get("trial_active"))
        trial_ends_at = company.get("trial_ends_at")
        days_remaining = 0
        if trial_ends_at:
            try:
                end = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
                delta = end - now
                days_remaining = max(0, delta.days)
                if end < now:
                    trial_active = False
            except (ValueError, TypeError):
                pass

        # Check any paid subscription on company
        subscription_active = False
        plan_id = None
        last_tx = await db.payment_transactions.find_one(
            {"company_id": company_id, "type": "subscription", "payment_status": "paid"},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        if last_tx:
            subscription_active = True
            plan_id = last_tx.get("plan_id")

        return {
            "trial_active": trial_active and not subscription_active,
            "trial_ends_at": trial_ends_at,
            "days_remaining": days_remaining,
            "subscription_active": subscription_active,
            "plan_id": plan_id,
            "downloads_allowed": subscription_active,  # Trial blocks all downloads
        }


class DownloadGateService:

    @staticmethod
    async def check_access(company_id: str, user_id: str, resource_id: str) -> Dict[str, Any]:
        """
        Check if user can download a resource right now.
        Returns {allowed: bool, reason: str, needs_payment: bool}
        """
        # Sandbox / demo companies bypass the £5 paywall (intentional for sales tour)
        company = await db.companies.find_one({"company_id": company_id}, {"_id": 0}) or {}
        if company.get("is_sandbox") or company.get("demo_mode"):
            return {"allowed": True, "reason": "Sandbox demo bypass", "needs_payment": False}

        status = await TrialService.get_trial_status(company_id)

        if status["trial_active"]:
            return {
                "allowed": False,
                "reason": "Downloads are disabled during the free trial. Upgrade your plan to enable downloads.",
                "needs_payment": False,
                "trial_active": True,
            }

        # Check for an unused, unexpired download pass for this resource+user
        now = datetime.now(timezone.utc).isoformat()
        pass_doc = await db.download_passes.find_one({
            "company_id": company_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "used": False,
            "expires_at": {"$gt": now},
        }, {"_id": 0})
        if pass_doc:
            return {"allowed": True, "reason": "Valid pass", "needs_payment": False, "pass_id": pass_doc["pass_id"]}

        # No pass → payment required (only if subscription_active gets free downloads — NO, per spec every payslip is £5)
        return {
            "allowed": False,
            "reason": f"Payment required — £{PAYSLIP_DOWNLOAD_PRICE:.2f} per payslip download",
            "needs_payment": True,
            "price": PAYSLIP_DOWNLOAD_PRICE,
            "currency": PAYSLIP_DOWNLOAD_CURRENCY,
        }

    @staticmethod
    async def consume_pass(pass_id: str) -> bool:
        """Mark a pass as used (single-use)"""
        now = datetime.now(timezone.utc).isoformat()
        result = await db.download_passes.update_one(
            {"pass_id": pass_id, "used": False},
            {"$set": {"used": True, "used_at": now}}
        )
        return result.modified_count > 0

    @staticmethod
    async def issue_pass(
        company_id: str,
        user_id: str,
        resource_id: str,
        resource_type: str = "payslip",
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a download pass (used after successful Stripe payment)"""
        now = datetime.now(timezone.utc)
        pass_id = f"dlp_{uuid.uuid4().hex[:14]}"
        await db.download_passes.insert_one({
            "pass_id": pass_id,
            "company_id": company_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "transaction_id": transaction_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=DOWNLOAD_PASS_VALIDITY_MINUTES)).isoformat(),
            "used": False,
        })
        return {"pass_id": pass_id, "expires_in_minutes": DOWNLOAD_PASS_VALIDITY_MINUTES}


trial_service = TrialService()
download_gate = DownloadGateService()
