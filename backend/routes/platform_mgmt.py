"""
RealtouchHR - Platform Plans + Modules + Tenant Management Extensions
Adds:
- Super-admin CRUD on subscription plans (dynamic pricing override)
- Super-admin module toggle per tenant (e.g., disable Performance for tenant X)
- Company-admin module visibility (read-only check)
- Company-admin data export (full tenant dump)
- Company-admin security settings (force-2FA for staff)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
import os, sys, uuid, io, json, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(tags=["Platform Management"])

PLATFORM_ADMIN_EMAILS = [
    e.strip().lower()
    for e in (os.environ.get("PLATFORM_ADMINS", "") or "").split(",")
    if e.strip()
]


# Modules that can be toggled per-tenant (matches sidebar nav)
AVAILABLE_MODULES = [
    {"key": "performance", "name": "Performance Management"},
    {"key": "cases", "name": "Employee Cases"},
    {"key": "training", "name": "Training Records"},
    {"key": "policies", "name": "Policies"},
    {"key": "absence", "name": "Absence & Sickness"},
    {"key": "hr_analytics", "name": "HR Analytics"},
    {"key": "ai_copilot", "name": "AI Copilot"},
    {"key": "ukvi", "name": "UKVI Compliance"},
    {"key": "rtw", "name": "Right to Work"},
    {"key": "cos", "name": "Certificates of Sponsorship"},
    {"key": "pensions", "name": "Pension Auto-Enrolment"},
    {"key": "hmrc_rti", "name": "HMRC RTI"},
    {"key": "statutory", "name": "Statutory Payments"},
    {"key": "year_end", "name": "Year-End Forms (P60/P45)"},
    {"key": "time_scheduling", "name": "Time & Scheduling"},
    {"key": "trust_badge", "name": "Trust Badge"},
    {"key": "dpo", "name": "Data Protection Centre"},
]


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None
    is_platform_admin: bool = False

    class Config:
        extra = "ignore"


async def _resolve_user(request: Request) -> CurrentUser:
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
    email = (user_doc.get("email") or "").lower()
    if email in PLATFORM_ADMIN_EMAILS:
        user_doc["is_platform_admin"] = True
    return CurrentUser(**user_doc)


async def get_platform_admin(request: Request) -> CurrentUser:
    user = await _resolve_user(request)
    if not user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform admin only")
    return user


async def get_company_owner(request: Request) -> CurrentUser:
    user = await _resolve_user(request)
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Company owner/admin only")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    return user


# ============================================================
#  PLATFORM PLANS CRUD (super admin)
# ============================================================

class PlanUpsert(BaseModel):
    plan_id: str  # 'starter' | 'professional' | 'enterprise' | custom
    name: str
    price: float
    currency: str = "gbp"
    employee_limit: int = 10
    features: List[str] = []
    active: bool = True


@router.get("/super-admin/plans")
async def admin_list_plans(_: CurrentUser = Depends(get_platform_admin)):
    """List configured plans. Defaults come from SUBSCRIPTION_PLANS unless overridden in DB."""
    from services.payment_service import SUBSCRIPTION_PLANS
    overrides = await db.platform_plans.find({}, {"_id": 0}).to_list(length=100)
    by_id = {o["plan_id"]: o for o in overrides}

    out = []
    for pid, p in SUBSCRIPTION_PLANS.items():
        merged = dict(p)
        merged["plan_id"] = pid
        merged["overridden"] = pid in by_id
        if pid in by_id:
            o = by_id[pid]
            merged.update({k: v for k, v in o.items() if k not in ("_id", "created_at", "updated_at")})
        merged.setdefault("active", True)
        out.append(merged)
    # Custom plans (only in DB)
    for o in overrides:
        if o["plan_id"] not in SUBSCRIPTION_PLANS:
            out.append({**o, "overridden": True})
    return {"plans": out}


@router.put("/super-admin/plans/{plan_id}")
async def admin_upsert_plan(plan_id: str, data: PlanUpsert, admin: CurrentUser = Depends(get_platform_admin)):
    """Save an override / new plan to platform_plans collection."""
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "plan_id": plan_id, "name": data.name, "price": data.price,
        "currency": data.currency, "employee_limit": data.employee_limit,
        "features": data.features, "active": data.active,
        "updated_at": now, "updated_by": admin.user_id,
    }
    await db.platform_plans.update_one(
        {"plan_id": plan_id},
        {"$set": record, "$setOnInsert": {"created_at": now, "created_by": admin.user_id}},
        upsert=True
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": None, "user_id": admin.user_id, "user_name": admin.name,
        "action": "platform_plan_updated", "entity_type": "plan", "entity_id": plan_id,
        "details": {"price": data.price}, "timestamp": now
    })
    return {"ok": True, "plan_id": plan_id}


@router.delete("/super-admin/plans/{plan_id}")
async def admin_delete_plan(plan_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    await db.platform_plans.delete_one({"plan_id": plan_id})
    return {"ok": True}


# ============================================================
#  PER-TENANT MODULE TOGGLE (super admin + company admin read)
# ============================================================

@router.get("/super-admin/modules")
async def list_modules(_: CurrentUser = Depends(get_platform_admin)):
    return {"modules": AVAILABLE_MODULES}


@router.get("/super-admin/companies/{company_id}/modules")
async def admin_get_company_modules(company_id: str, _: CurrentUser = Depends(get_platform_admin)):
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0, "modules_disabled": 1, "name": 1})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    disabled = set(company.get("modules_disabled") or [])
    out = [{"key": m["key"], "name": m["name"], "enabled": m["key"] not in disabled} for m in AVAILABLE_MODULES]
    return {"company_id": company_id, "company_name": company.get("name"), "modules": out}


class ModuleToggle(BaseModel):
    module_key: str
    enabled: bool


@router.post("/super-admin/companies/{company_id}/modules")
async def admin_toggle_company_module(company_id: str, data: ModuleToggle, admin: CurrentUser = Depends(get_platform_admin)):
    valid = {m["key"] for m in AVAILABLE_MODULES}
    if data.module_key not in valid:
        raise HTTPException(status_code=400, detail="Unknown module")
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0, "modules_disabled": 1})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    disabled = set(company.get("modules_disabled") or [])
    if data.enabled:
        disabled.discard(data.module_key)
    else:
        disabled.add(data.module_key)
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"modules_disabled": list(disabled), "modules_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id, "user_id": admin.user_id, "user_name": admin.name,
        "action": "platform_module_toggle", "entity_type": "module", "entity_id": data.module_key,
        "details": {"enabled": data.enabled}, "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"ok": True, "modules_disabled": list(disabled)}


@router.get("/my-modules")
async def my_modules(user: CurrentUser = Depends(_resolve_user)):
    """Any authenticated user: returns the modules enabled for their tenant. Frontend uses this to hide menu items."""
    if not user.company_id:
        return {"modules": AVAILABLE_MODULES, "disabled": []}
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0, "modules_disabled": 1})
    disabled = set((company or {}).get("modules_disabled") or [])
    enabled_modules = [{"key": m["key"], "name": m["name"]} for m in AVAILABLE_MODULES if m["key"] not in disabled]
    return {"modules": enabled_modules, "disabled": list(disabled)}


# ============================================================
#  COMPANY ADMIN — FULL TENANT DATA EXPORT
# ============================================================

@router.get("/company/data-export")
async def company_data_export(user: CurrentUser = Depends(get_company_owner)):
    """
    Owner/admin downloads a complete export of every record in their tenant.
    Useful for: GDPR compliance, switching providers, internal audit, regulator request.
    """
    company_id = user.company_id
    bundle: Dict[str, Any] = {
        "export_id": f"company_export_{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.email,
        "company_id": company_id,
        "data": {},
    }

    collections = [
        "companies", "employees", "leave_requests", "documents", "shifts", "timesheets",
        "payslips", "pay_runs", "audit_log", "notifications", "rtw_checks", "cos_register",
        "pension_enrolments", "pension_schemes", "statutory_payments", "performance_objectives",
        "performance_appraisals", "performance_notes", "employee_cases", "secure_documents",
        "payment_transactions", "download_passes", "tax_documents", "p11d_records",
        "policies", "policy_acknowledgements", "policy_versions",
        "training_courses", "training_records",
        "absence_records",
        "data_processing_activities", "dsar_requests", "breach_incidents",
        "processors_register", "retention_overrides", "dpia_records",
        "users",  # team list (no password hashes / 2FA secrets)
    ]
    for c in collections:
        try:
            q = {"company_id": company_id}
            # Special: companies is fetched by company_id field directly
            projection = {"_id": 0, "password_hash": 0, "totp_secret": 0, "backup_codes_hashed": 0}
            docs = await db[c].find(q, projection).to_list(length=20000)
            if docs:
                bundle["data"][c] = docs
        except Exception:
            pass

    bundle["summary"] = {
        "total_collections": len(bundle["data"]),
        "total_records": sum(len(v) for v in bundle["data"].values()),
        "collections": {k: len(v) for k, v in bundle["data"].items()},
    }

    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id, "user_id": user.user_id, "user_name": user.name,
        "action": "company.data_exported", "entity_type": "company", "entity_id": company_id,
        "details": {"records": bundle["summary"]["total_records"]},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    body = json.dumps(bundle, indent=2, default=str).encode("utf-8")
    filename = f"realtouchhr_company_export_{company_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    return StreamingResponse(
        io.BytesIO(body),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============================================================
#  COMPANY ADMIN — SECURITY SETTINGS
# ============================================================

class SecurityPolicy(BaseModel):
    force_2fa_for_admins: bool = False
    force_2fa_for_all: bool = False
    session_timeout_minutes: int = 60 * 24 * 7  # 7 days
    password_min_length: int = 8


@router.get("/company/security-policy")
async def get_security_policy(user: CurrentUser = Depends(get_company_owner)):
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0, "security_policy": 1})
    policy = (company or {}).get("security_policy") or SecurityPolicy().dict()
    # Stats
    total_admins = await db.users.count_documents({"company_id": user.company_id, "role": {"$in": ["owner", "admin"]}})
    twofa_enabled_count = await db.user_2fa.count_documents({
        "user_id": {"$in": [u["user_id"] for u in await db.users.find({"company_id": user.company_id}, {"_id": 0, "user_id": 1}).to_list(length=500)]},
        "enabled": True
    })
    total_users = await db.users.count_documents({"company_id": user.company_id})
    return {
        "policy": policy,
        "stats": {
            "total_users": total_users,
            "total_admins": total_admins,
            "twofa_enabled_count": twofa_enabled_count,
            "twofa_coverage_percent": round(twofa_enabled_count / max(1, total_users) * 100, 1)
        }
    }


@router.put("/company/security-policy")
async def update_security_policy(data: SecurityPolicy, user: CurrentUser = Depends(get_company_owner)):
    await db.companies.update_one(
        {"company_id": user.company_id},
        {"$set": {"security_policy": data.dict(), "security_policy_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id, "user_id": user.user_id, "user_name": user.name,
        "action": "company.security_policy_updated", "entity_type": "company", "entity_id": user.company_id,
        "details": data.dict(), "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"ok": True, "policy": data.dict()}
