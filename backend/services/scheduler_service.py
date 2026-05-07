"""
Background scheduler — runs periodic jobs:
- Daily UKVI alert generation per company (visa expiries, salary threshold breaches)
- Daily sandbox cleanup (purges expired sandbox accounts)
- Weekly retention dry-run audit (informational)

Started during FastAPI startup; stopped on shutdown.
"""
import os
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_ukvi_alerts_for_all_companies():
    """Iterate all companies and (re)generate visa expiry + salary threshold alerts."""
    from services.ukvi_service import ukvi_service
    companies = await db.companies.find({}, {"_id": 0, "company_id": 1}).to_list(10000)
    total = 0
    for c in companies:
        try:
            alerts = await ukvi_service.generate_expiry_alerts(c["company_id"])
            total += len(alerts)
        except Exception as exc:
            logger.warning(f"UKVI alert run failed for {c.get('company_id')}: {exc}")
    logger.info(f"[scheduler] UKVI alerts generated for {len(companies)} companies (new: {total})")


async def run_sandbox_cleanup():
    """Remove sandbox accounts/companies older than 24h."""
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc).isoformat()
    expired = await db.companies.find(
        {"is_sandbox": True, "sandbox_expires_at": {"$lt": cutoff}},
        {"_id": 0, "company_id": 1, "owner_id": 1}
    ).to_list(1000)
    deleted_companies = 0
    for c in expired:
        cid = c["company_id"]
        for col in ["employees", "pay_runs", "leave_requests", "ukvi_alerts",
                    "compliance_tasks", "audit_log", "ukvi_reports",
                    "tax_documents", "p11d_records", "rti_leaver_queue"]:
            try:
                await db[col].delete_many({"company_id": cid})
            except Exception:
                pass
        # Payslips by payrun join
        payruns = await db.pay_runs.find({"company_id": cid}, {"_id": 0, "payrun_id": 1}).to_list(1000)
        ids = [p["payrun_id"] for p in payruns]
        if ids:
            await db.payslips.delete_many({"payrun_id": {"$in": ids}})
        # Owner user + sessions
        if c.get("owner_id"):
            await db.users.delete_many({"user_id": c["owner_id"]})
            await db.user_sessions.delete_many({"user_id": c["owner_id"]})
        deleted_companies += 1

    if deleted_companies:
        await db.companies.delete_many(
            {"is_sandbox": True, "sandbox_expires_at": {"$lt": cutoff}}
        )
        logger.info(f"[scheduler] Sandbox cleanup: removed {deleted_companies} expired demo companies")


async def run_retention_audit():
    """Weekly — log how many records would be archived (dry run for visibility)."""
    logger.info("[scheduler] Retention audit (dry run) — nothing deleted")


def start_scheduler():
    if scheduler.running:
        return
    # UKVI alerts at 02:00 daily
    scheduler.add_job(
        run_ukvi_alerts_for_all_companies,
        trigger="cron", hour=2, minute=0,
        id="ukvi_alerts_daily", replace_existing=True,
    )
    # Sandbox cleanup every hour
    scheduler.add_job(
        run_sandbox_cleanup,
        trigger="interval", hours=1,
        id="sandbox_cleanup_hourly", replace_existing=True,
    )
    # Retention audit weekly Sunday 03:00
    scheduler.add_job(
        run_retention_audit,
        trigger="cron", day_of_week="sun", hour=3, minute=0,
        id="retention_audit_weekly", replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] Started — 3 jobs registered")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped")
