"""
Super Admin Routes — Platform Owner Control Plane
Restricted to users whose email is listed in PLATFORM_ADMINS env (comma-separated)
or who have is_platform_admin=true in users collection.

Capabilities:
- View / suspend / restore companies
- View all subscriptions + payments
- Toggle feature flags per company
- Impersonate company users (with full audit)
- View platform-wide audit log
- Emergency controls (kill switch)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, sys, uuid, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


PLATFORM_ADMIN_EMAILS = [
    e.strip().lower()
    for e in (os.environ.get("PLATFORM_ADMINS", "") or "").split(",")
    if e.strip()
]


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None
    is_platform_admin: bool = False


async def get_platform_admin(request: Request) -> CurrentUser:
    """Require platform admin access — checks PLATFORM_ADMINS env OR is_platform_admin=true on user record."""
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
    is_admin = (
        user_doc.get("is_platform_admin") is True
        or email in PLATFORM_ADMIN_EMAILS
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Platform admin only")

    user_doc["is_platform_admin"] = True
    return CurrentUser(**user_doc)


# ==================== METRICS ====================

@router.get("/metrics")
async def platform_metrics(_: CurrentUser = Depends(get_platform_admin)):
    """Top-level metrics for the super admin dashboard"""
    total_companies = await db.companies.count_documents({})
    active_companies = await db.companies.count_documents({"setup_completed": True, "$or": [{"is_sandbox": {"$ne": True}}]})
    trial_companies = await db.companies.count_documents({"trial_active": True})
    sandbox_companies = await db.companies.count_documents({"is_sandbox": True})
    suspended_companies = await db.companies.count_documents({"suspended": True})
    total_users = await db.users.count_documents({"is_sandbox": {"$ne": True}})
    total_employees = await db.employees.count_documents({})
    paid_subs = await db.payment_transactions.count_documents(
        {"type": "subscription", "payment_status": "paid"}
    )
    # MRR estimate from latest paid subscription per company
    mrr_pipeline = [
        {"$match": {"type": "subscription", "payment_status": "paid"}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$company_id", "amount": {"$first": "$amount"}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    mrr_result = await db.payment_transactions.aggregate(mrr_pipeline).to_list(1)
    mrr = mrr_result[0]["total"] if mrr_result else 0

    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "trial_companies": trial_companies,
        "sandbox_companies": sandbox_companies,
        "suspended_companies": suspended_companies,
        "total_users": total_users,
        "total_employees": total_employees,
        "paid_subscriptions": paid_subs,
        "mrr_gbp": round(mrr, 2),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


# ==================== COMPANIES ====================

@router.get("/companies")
async def list_companies(
    search: Optional[str] = None,
    status: Optional[str] = None,
    _: CurrentUser = Depends(get_platform_admin)
):
    """List all companies on the platform"""
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if status == "trial":
        query["trial_active"] = True
    elif status == "active":
        query["setup_completed"] = True
        query["trial_active"] = {"$ne": True}
    elif status == "suspended":
        query["suspended"] = True
    elif status == "sandbox":
        query["is_sandbox"] = True

    companies = await db.companies.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for c in companies:
        c["employee_count"] = await db.employees.count_documents({"company_id": c["company_id"]})
        c["user_count"] = await db.users.count_documents({"company_id": c["company_id"]})
    return {"companies": companies, "total": len(companies)}


@router.get("/companies/{company_id}")
async def get_company_detail(company_id: str, _: CurrentUser = Depends(get_platform_admin)):
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    users = await db.users.find({"company_id": company_id}, {"_id": 0, "password_hash": 0}).to_list(500)
    employees_count = await db.employees.count_documents({"company_id": company_id})
    txs = await db.payment_transactions.find(
        {"company_id": company_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {
        "company": company,
        "users": users,
        "employees_count": employees_count,
        "recent_transactions": txs,
    }


@router.post("/companies/{company_id}/suspend")
async def suspend_company(
    company_id: str,
    data: dict,
    admin: CurrentUser = Depends(get_platform_admin)
):
    reason = data.get("reason", "Manual suspension by platform admin")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"suspended": True, "suspended_at": now, "suspended_reason": reason}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": admin.user_id,
        "user_name": admin.name,
        "action": "platform_company_suspended",
        "entity_type": "company",
        "entity_id": company_id,
        "details": {"reason": reason},
        "timestamp": now,
    })
    return {"message": "Company suspended"}


@router.post("/companies/{company_id}/restore")
async def restore_company(company_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    now = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"suspended": False}, "$unset": {"suspended_at": "", "suspended_reason": ""}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": admin.user_id,
        "user_name": admin.name,
        "action": "platform_company_restored",
        "entity_type": "company",
        "entity_id": company_id,
        "details": {},
        "timestamp": now,
    })
    return {"message": "Company restored"}


# ==================== FEATURE FLAGS ====================

@router.get("/feature-flags")
async def list_global_flags(_: CurrentUser = Depends(get_platform_admin)):
    """Platform-wide feature flags"""
    flags = await db.feature_flags.find({"scope": "global"}, {"_id": 0}).to_list(200)
    return {"flags": flags, "total": len(flags)}


@router.put("/feature-flags/{flag_key}")
async def set_global_flag(flag_key: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    enabled = bool(data.get("enabled", False))
    now = datetime.now(timezone.utc).isoformat()
    await db.feature_flags.update_one(
        {"scope": "global", "key": flag_key},
        {"$set": {
            "key": flag_key,
            "scope": "global",
            "enabled": enabled,
            "description": data.get("description", ""),
            "updated_at": now,
            "updated_by": admin.user_id,
        }},
        upsert=True
    )
    return {"key": flag_key, "enabled": enabled}


@router.put("/companies/{company_id}/feature-flags/{flag_key}")
async def set_company_flag(
    company_id: str,
    flag_key: str,
    data: dict,
    admin: CurrentUser = Depends(get_platform_admin)
):
    enabled = bool(data.get("enabled", False))
    now = datetime.now(timezone.utc).isoformat()
    await db.feature_flags.update_one(
        {"scope": "company", "key": flag_key, "company_id": company_id},
        {"$set": {
            "key": flag_key,
            "scope": "company",
            "company_id": company_id,
            "enabled": enabled,
            "updated_at": now,
            "updated_by": admin.user_id,
        }},
        upsert=True
    )
    return {"company_id": company_id, "key": flag_key, "enabled": enabled}


# ==================== IMPERSONATION ====================

@router.post("/impersonate")
async def impersonate_user(data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """
    Issue a short-lived (30-min) token that the platform admin can use to act
    as another user. Every action while impersonating is logged with both
    actor (admin) + impersonated user IDs.
    """
    target_user_id = data.get("user_id")
    reason = data.get("reason", "Support investigation")
    if not target_user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    target = await db.users.find_one({"user_id": target_user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    now = datetime.now(timezone.utc)
    session_token = jwt.encode(
        {
            "user_id": target_user_id,
            "email": target.get("email"),
            "impersonator_id": admin.user_id,
            "impersonator_name": admin.name,
            "is_impersonation": True,
            "exp": now + timedelta(minutes=30),
        },
        JWT_SECRET, algorithm="HS256"
    )

    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": target_user_id,
        "is_impersonation": True,
        "impersonator_id": admin.user_id,
        "impersonator_name": admin.name,
        "reason": reason,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
    })

    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": target.get("company_id"),
        "user_id": admin.user_id,
        "user_name": admin.name,
        "action": "user_impersonated",
        "entity_type": "user",
        "entity_id": target_user_id,
        "details": {
            "target_email": target.get("email"),
            "target_role": target.get("role"),
            "reason": reason,
        },
        "timestamp": now.isoformat(),
    })

    return {
        "token": session_token,
        "expires_in_minutes": 30,
        "target_user": {
            "user_id": target_user_id,
            "email": target.get("email"),
            "name": target.get("name"),
            "company_id": target.get("company_id"),
        }
    }


# ==================== PLATFORM AUDIT LOG ====================

@router.get("/audit-log")
async def platform_audit_log(
    limit: int = 100,
    action: Optional[str] = None,
    _: CurrentUser = Depends(get_platform_admin)
):
    query = {}
    if action:
        query["action"] = action
    logs = await db.audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"audit_log": logs, "total": len(logs)}


# ==================== EMERGENCY CONTROLS ====================

@router.post("/emergency/kill-switch")
async def emergency_kill_switch(data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """
    Emergency: globally disable ALL paid features for ALL companies.
    Sets a global feature_flag platform.kill_switch=true.
    """
    enabled = bool(data.get("enabled", False))
    reason = data.get("reason", "Emergency activation by platform admin")
    now = datetime.now(timezone.utc).isoformat()
    await db.feature_flags.update_one(
        {"scope": "global", "key": "platform.kill_switch"},
        {"$set": {
            "key": "platform.kill_switch", "scope": "global",
            "enabled": enabled, "description": reason,
            "updated_at": now, "updated_by": admin.user_id,
        }},
        upsert=True
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": "platform",
        "user_id": admin.user_id,
        "user_name": admin.name,
        "action": "kill_switch_toggled",
        "entity_type": "platform",
        "entity_id": "kill_switch",
        "details": {"enabled": enabled, "reason": reason},
        "timestamp": now,
    })
    return {"kill_switch_enabled": enabled, "reason": reason}
