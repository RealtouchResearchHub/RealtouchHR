"""Admin endpoints — Record Retention enforcement, Student Loan rates."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, sys, uuid, jwt, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


# Default UK retention windows (days)
RETENTION_POLICY = {
    "audit_log": 365 * 7,           # 7 years (HMRC)
    "payslips": 365 * 6,            # 6 years
    "rti_submissions": 365 * 6,
    "tax_documents": 365 * 6,       # P45/P60/P11D
    "p11d_records": 365 * 6,
    "leave_requests": 365 * 6,
    "ukvi_alerts": 365 * 1,         # Resolved alerts older than 1 year
    "notifications": 90,
}


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            token = auth.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    else:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


async def require_admin_role(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Enforce that the caller has owner or admin role on all Admin Portal routes."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin Portal access requires the Owner or Administrator role."
        )
    return user


@router.get("/retention/policy")
async def get_retention_policy(user: CurrentUser = Depends(require_admin_role)):
    """Return the retention policy in days"""
    return {"retention_days": RETENTION_POLICY, "description": "UK HMRC standard 6-7 year retention for payroll and tax records."}


@router.post("/retention/run")
async def run_retention(dry_run: bool = True, user: CurrentUser = Depends(require_admin_role)):
    """Archive (or count) records older than retention windows. Owner or admin."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    now = datetime.now(timezone.utc)
    company_id = user.company_id
    summary = {}

    fields_by_collection = {
        "audit_log": "timestamp",
        "payslips": None,  # will use payrun pay_date join — skip
        "rti_submissions": "created_at",
        "tax_documents": "generated_at",
        "p11d_records": "updated_at",
        "leave_requests": "created_at",
        "ukvi_alerts": "created_at",
        "notifications": "created_at",
    }

    for collection, days in RETENTION_POLICY.items():
        ts_field = fields_by_collection.get(collection)
        if not ts_field:
            summary[collection] = {"skipped": True, "reason": "no timestamp field configured"}
            continue
        cutoff = (now - timedelta(days=days)).isoformat()
        query = {"company_id": company_id, ts_field: {"$lt": cutoff}}
        # ukvi_alerts: only delete resolved
        if collection == "ukvi_alerts":
            query["resolved"] = True
        # notifications: only read
        if collection == "notifications":
            query["read"] = True
        coll = db[collection]
        count = await coll.count_documents(query)
        if dry_run:
            summary[collection] = {"would_archive": count, "cutoff": cutoff}
        else:
            # Move to {collection}_archive then delete
            if count > 0:
                docs = await coll.find(query).to_list(100000)
                if docs:
                    await db[f"{collection}_archive"].insert_many(docs)
                    await coll.delete_many(query)
            summary[collection] = {"archived": count, "cutoff": cutoff}

    audit_id = f"audit_{uuid.uuid4().hex[:12]}"
    await db.audit_log.insert_one({
        "audit_id": audit_id,
        "company_id": company_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "action": "retention_run",
        "entity_type": "system",
        "entity_id": "retention",
        "details": {"dry_run": dry_run, "summary": summary},
        "timestamp": now.isoformat(),
    })

    return {"dry_run": dry_run, "summary": summary, "audit_id": audit_id}


@router.get("/student-loans/plans")
async def get_student_loan_plans(user: CurrentUser = Depends(require_admin_role)):
    """Return UK student loan plans + 2025-26 thresholds for UI dropdowns."""
    from services.student_loan_service import get_plans
    return {"plans": get_plans(), "tax_year": "2025-26"}


# ---------------------------------------------------------------------------
# Company Module & Feature Flag settings (company admin level)
# ---------------------------------------------------------------------------

AVAILABLE_MODULES = [
    {"key": "payroll", "label": "Payroll", "plan_required": "starter"},
    {"key": "hmrc_rti", "label": "HMRC RTI", "plan_required": "professional"},
    {"key": "ukvi_compliance", "label": "UKVI Compliance", "plan_required": "starter"},
    {"key": "leave_management", "label": "Leave Management", "plan_required": "starter"},
    {"key": "performance", "label": "Performance", "plan_required": "professional"},
    {"key": "training", "label": "Training", "plan_required": "professional"},
    {"key": "documents", "label": "Documents", "plan_required": "starter"},
    {"key": "time_tracking", "label": "Time Tracking", "plan_required": "starter"},
    {"key": "hr_analytics", "label": "HR Analytics", "plan_required": "professional"},
    {"key": "gdpr", "label": "GDPR Centre", "plan_required": "professional"},
    {"key": "scheduling", "label": "Scheduling", "plan_required": "starter"},
    {"key": "statutory_pay", "label": "Statutory Pay", "plan_required": "professional"},
    {"key": "year_end", "label": "Year-End", "plan_required": "professional"},
    {"key": "self_service", "label": "Employee Self-Service", "plan_required": "starter"},
    {"key": "ai_copilot", "label": "AI Copilot", "plan_required": "starter"},
]


class ModuleToggle(BaseModel):
    module_key: str
    enabled: bool


@router.get("/modules")
async def get_company_modules(user: CurrentUser = Depends(require_admin_role)):
    """Return module enable/disable state for this company."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0, "modules_disabled": 1, "subscription_plan": 1})
    disabled_set = set(company.get("modules_disabled") or [])
    plan = (company.get("subscription_plan") or "free").lower()
    modules_state = [
        {**m, "enabled": m["key"] not in disabled_set}
        for m in AVAILABLE_MODULES
    ]
    return {"modules": modules_state, "plan": plan}


@router.patch("/modules/{module_key}")
async def toggle_company_module(module_key: str, body: ModuleToggle, user: CurrentUser = Depends(require_admin_role)):
    """Enable or disable a module for this company."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    valid = {m["key"] for m in AVAILABLE_MODULES}
    if module_key not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown module: {module_key}")

    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0, "modules_disabled": 1})
    disabled = set(company.get("modules_disabled") or [])

    if body.enabled:
        disabled.discard(module_key)
    else:
        disabled.add(module_key)

    await db.companies.update_one(
        {"company_id": user.company_id},
        {"$set": {"modules_disabled": list(disabled), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    await db.audit_log.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "action": "module_toggle",
        "entity_type": "module",
        "entity_id": module_key,
        "details": {"enabled": body.enabled, "module_key": module_key},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"module_key": module_key, "enabled": body.enabled}


# ---------------------------------------------------------------------------
# Danger Zone re-authentication
# ---------------------------------------------------------------------------

class ReauthRequest(BaseModel):
    password: str


@router.post("/danger-zone/verify")
async def verify_danger_zone(body: ReauthRequest, user: CurrentUser = Depends(require_admin_role)):
    """Verify the admin's password before executing Danger Zone operations."""
    import bcrypt as _bcrypt
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "password_hash": 1})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Password-based authentication not configured for this account. Use SSO or contact support.")
    ok = _bcrypt.checkpw(body.password.encode(), user_doc["password_hash"].encode())
    if not ok:
        raise HTTPException(status_code=403, detail="Incorrect password.")
    return {"verified": True}


# ---------------------------------------------------------------------------
# Payroll engine status — sandbox / provider / live RTI & pension state
# ---------------------------------------------------------------------------

@router.get("/payroll-engine-status")
async def get_payroll_engine_status(user: CurrentUser = Depends(require_admin_role)):
    """
    Status of the payroll/RTI/pension safety engine for this company.

    Reflects whether live HMRC RTI submission and pension provider integration
    are enabled — both default off until a real embedded payroll provider or
    HMRC Gateway integration is connected.
    """
    from feature_flags import get_all_flags
    from services.rti_sync_service import rti_sync_engine

    flags = await get_all_flags()
    company_id = user.company_id

    last_error = None
    last_live_submission = None
    last_simulated = None
    if company_id:
        last_error = await db.rti_submissions.find_one(
            {"company_id": company_id, "status": {"$in": ["error", "rejected", "validation_failed"]}},
            {"_id": 0, "submission_id": 1, "status": 1, "created_at": 1, "submission_type": 1},
            sort=[("created_at", -1)]
        )
        last_live_submission = await db.rti_receipts.find_one(
            {"company_id": company_id, "is_simulated": False},
            {"_id": 0, "submission_id": 1, "created_at": 1},
            sort=[("created_at", -1)]
        )
        last_simulated = await db.rti_submissions.find_one(
            {"company_id": company_id, "is_simulated": True},
            {"_id": 0, "submission_id": 1, "created_at": 1, "submission_type": 1},
            sort=[("created_at", -1)]
        )

    live_rti_enabled = rti_sync_engine._feature_flags["live_submission"] and rti_sync_engine.mode.value == "live"

    if live_rti_enabled and flags["payroll_embedded_provider"]:
        current_mode = "live-enabled"
    elif flags["payroll_embedded_provider"]:
        current_mode = "provider-connected"
    else:
        current_mode = "sandbox"

    return {
        "payroll_native_sandbox_active": flags["payroll_native_sandbox"],
        "embedded_provider_connected": flags["payroll_embedded_provider"],
        "live_rti_enabled": live_rti_enabled,
        "pension_integration_enabled": flags["pension_integration_enabled"],
        "legacy_hmrc_route_disabled": flags["rti_legacy_hmrc_disabled"],
        "provider_name": None,
        "last_provider_sync": None,
        "last_live_submission": last_live_submission,
        "last_simulated_submission": last_simulated,
        "last_error": last_error,
        "current_mode": current_mode,
    }
