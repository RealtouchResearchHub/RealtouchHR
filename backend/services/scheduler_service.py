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


async def run_trial_expiry_reminder():
    """Daily: email owners whose trial ends in 3 days."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    target_min = (now + timedelta(days=3)).isoformat()
    target_max = (now + timedelta(days=3, hours=23)).isoformat()
    companies = await db.companies.find({
        "trial_active": True,
        "trial_ends_at": {"$gte": target_min, "$lte": target_max},
    }, {"_id": 0}).to_list(1000)
    sent = 0
    for c in companies:
        if c.get("trial_reminder_sent"):
            continue
        try:
            owner = await db.users.find_one({"user_id": c.get("owner_id")}, {"_id": 0})
            if owner and owner.get("email"):
                from services.email_service import email_service, get_base_template
                html = get_base_template(f"""
                    <h2 style="color: #111827;">Your RealtouchHR trial ends in 3 days</h2>
                    <p style="color: #374151;">Hi {owner.get('name', 'there')},</p>
                    <p style="color: #374151; line-height: 1.6;">
                        Your free trial for <strong>{c.get('name', 'your company')}</strong> ends on
                        <strong>{c.get('trial_ends_at', '')[:10]}</strong>. Upgrade now to keep uninterrupted access
                        and unlock payslip downloads.
                    </p>
                    <div style="margin: 24px 0;">
                        <a href="{os.environ.get('APP_URL', 'https://realtouchhr.com')}/billing"
                            style="display:inline-block; background:#4f46e5; color:#fff; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:600;">
                            Upgrade now
                        </a>
                    </div>
                """)
                await email_service.send_email(owner["email"], "Trial ends in 3 days - RealtouchHR", html)
                sent += 1
                await db.companies.update_one(
                    {"company_id": c["company_id"]},
                    {"$set": {"trial_reminder_sent": True, "trial_reminder_sent_at": now.isoformat()}}
                )
        except Exception as exc:
            logger.warning(f"Trial reminder failed for {c.get('company_id')}: {exc}")
    logger.info(f"[scheduler] Trial expiry reminders sent: {sent}")


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
    # Daily trial expiry reminder at 09:00
    scheduler.add_job(
        run_trial_expiry_reminder,
        trigger="cron", hour=9, minute=0,
        id="trial_reminder_daily", replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] Started — 4 jobs registered")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped")
