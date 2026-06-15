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

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
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
        txns = await db.payment_transactions.find(
            {"company_id": company_id, "type": "subscription", "payment_status": "paid"},
            {"_id": 0}
        ).to_list(1000)
        last_tx = sorted(txns, key=lambda x: x.get("created_at", ""), reverse=True)[0] if txns else None
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
        Returns {allowed, reason, needs_payment, ...}

        Order of checks:
          1. Sandbox bypass
          2. Trial → block (no downloads)
          3. Existing single-use pass → consume + allow
          4. Active bulk-downloads window → allow (no consumption)
          5. Plan-based monthly free quota → allow + record usage
          6. Otherwise → 402 paywall
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # 1) Sandbox / demo bypass
        company = await db.companies.find_one({"company_id": company_id}, {"_id": 0}) or {}
        if company.get("is_sandbox") or company.get("demo_mode"):
            return {"allowed": True, "reason": "Sandbox demo bypass", "needs_payment": False}

        # 2) Trial blocks downloads
        status = await TrialService.get_trial_status(company_id)
        if status["trial_active"]:
            return {
                "allowed": False,
                "reason": "Downloads are disabled during the free trial. Upgrade your plan to enable downloads.",
                "needs_payment": False,
                "trial_active": True,
            }

        # 3) Existing single-use pass
        pass_doc = await db.download_passes.find_one({
            "company_id": company_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "used": False,
            "expires_at": {"$gt": now.isoformat()},
        }, {"_id": 0})
        if pass_doc:
            return {"allowed": True, "reason": "Valid pass", "needs_payment": False, "pass_id": pass_doc["pass_id"]}

        # 4) Bulk downloads package active?
        bulk_until = company.get("bulk_downloads_active_until")
        if bulk_until:
            try:
                bulk_dt = datetime.fromisoformat(bulk_until.replace("Z", "+00:00"))
                if bulk_dt > now:
                    return {
                        "allowed": True,
                        "reason": "Bulk downloads package active",
                        "needs_payment": False,
                        "bulk_active": True,
                        "bulk_until": bulk_until,
                    }
            except (ValueError, TypeError):
                pass

        # 5) Plan-based monthly free quota
        from services.payment_service import PLAN_DOWNLOAD_QUOTA
        plan_id = status.get("plan_id")
        quota = PLAN_DOWNLOAD_QUOTA.get(plan_id, 0)
        if quota != 0 and status.get("subscription_active"):
            month_key = now.strftime("%Y-%m")
            usage = await db.download_usage.find_one(
                {"company_id": company_id, "month": month_key}, {"_id": 0}
            ) or {"count": 0}
            used_count = usage.get("count", 0)
            if quota == -1 or used_count < quota:
                return {
                    "allowed": True,
                    "reason": "Within plan quota",
                    "needs_payment": False,
                    "quota_used": used_count,
                    "quota_limit": quota,
                    "plan_quota_consume": True,
                    "month_key": month_key,
                }
            # Quota exhausted → fall through to paywall

        # 6) Paywall
        return {
            "allowed": False,
            "reason": f"Payment required — £{PAYSLIP_DOWNLOAD_PRICE:.2f} per download. Upgrade to Professional for 50/month free, or buy unlimited £29/month.",
            "needs_payment": True,
            "price": PAYSLIP_DOWNLOAD_PRICE,
            "currency": PAYSLIP_DOWNLOAD_CURRENCY,
            "bulk_offer_price": 29.00,
            "bulk_offer_id": "bulk_downloads_monthly",
        }

    @staticmethod
    async def consume_quota(company_id: str, month_key: str) -> None:
        """Increment monthly download counter (idempotent — uses upsert + $inc)."""
        await db.download_usage.update_one(
            {"company_id": company_id, "month": month_key},
            {"$inc": {"count": 1}, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )

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
