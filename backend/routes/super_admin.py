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
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


def _get_platform_admin_emails():
    """Read fresh from env every call so no restart needed after .env change."""
    load_dotenv(ROOT_DIR / '.env', override=True)
    return [
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
        or email in _get_platform_admin_emails()
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


@router.post("/companies/{company_id}/extend-trial")
async def extend_trial(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    days = max(1, int(data.get("days", 14)))
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0, "trial_ends_at": 1})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        base = datetime.fromisoformat(company["trial_ends_at"]) if company.get("trial_ends_at") else datetime.now(timezone.utc)
    except Exception:
        base = datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    new_end = (base + timedelta(days=days)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"trial_ends_at": new_end, "trial_active": True}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id, "user_id": admin.user_id, "user_name": admin.name,
        "action": "trial_extended", "entity_type": "company", "entity_id": company_id,
        "details": {"days_added": days, "new_trial_ends_at": new_end}, "timestamp": now,
    })
    return {"ok": True, "new_trial_ends_at": new_end}


@router.post("/companies/{company_id}/set-plan")
async def set_company_plan(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    plan_id = data.get("plan_id")
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id required")
    now = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"plan_id": plan_id, "subscription_updated_at": now}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id, "user_id": admin.user_id, "user_name": admin.name,
        "action": "plan_changed", "entity_type": "company", "entity_id": company_id,
        "details": {"new_plan_id": plan_id}, "timestamp": now,
    })
    return {"ok": True, "plan_id": plan_id}


@router.post("/companies/{company_id}/delete")
async def delete_company(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    confirm = data.get("confirm")
    if confirm != company_id:
        raise HTTPException(status_code=400, detail="Pass confirm=company_id to confirm deletion")
    now = datetime.now(timezone.utc).isoformat()
    for col in ["employees", "users", "leave_requests", "documents", "payslips",
                "pay_runs", "audit_log", "shifts", "timesheets", "notifications"]:
        await db[col].delete_many({"company_id": company_id})
    await db.companies.delete_one({"company_id": company_id})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": "platform", "user_id": admin.user_id, "user_name": admin.name,
        "action": "company_deleted", "entity_type": "company", "entity_id": company_id,
        "details": {}, "timestamp": now,
    })
    return {"ok": True}


# ==================== USERS ====================

@router.get("/users")
async def list_all_users(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    _: CurrentUser = Depends(get_platform_admin)
):
    query = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]
    if company_id:
        query["company_id"] = company_id
    users = await db.users.find(
        query, {"_id": 0, "password_hash": 0, "totp_secret": 0, "backup_codes_hashed": 0}
    ).sort("created_at", -1).to_list(500)
    return {"users": users, "total": len(users)}


@router.post("/users/{user_id}/disable")
async def disable_user(user_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"user_id": user_id}, {"$set": {"disabled": True}})
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": None, "user_id": admin.user_id, "user_name": admin.name,
        "action": "user_disabled", "entity_type": "user", "entity_id": user_id,
        "details": {}, "timestamp": now,
    })
    return {"ok": True}


@router.post("/users/{user_id}/enable")
async def enable_user(user_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"user_id": user_id}, {"$set": {"disabled": False}})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": None, "user_id": admin.user_id, "user_name": admin.name,
        "action": "user_enabled", "entity_type": "user", "entity_id": user_id,
        "details": {}, "timestamp": now,
    })
    return {"ok": True}


@router.post("/users/{user_id}/remove")
async def remove_user(user_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Temporary removal — frees the email for fresh registration while the account can still be restored."""
    reason = data.get("reason", "Removed by platform admin")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("removed"):
        raise HTTPException(status_code=400, detail="Account is already removed")
    now = datetime.now(timezone.utc).isoformat()
    placeholder_email = f"removed+{user_id}@realtouchhr-removed.invalid"
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "removed": True,
            "removed_at": now,
            "removed_reason": reason,
            "original_email": user["email"],
            "email": placeholder_email,
            "disabled": True,
        }}
    )
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": None, "user_id": admin.user_id, "user_name": admin.name,
        "action": "user_removed", "entity_type": "user", "entity_id": user_id,
        "details": {"reason": reason, "freed_email": user["email"]}, "timestamp": now,
    })
    return {"ok": True}


@router.post("/users/{user_id}/restore")
async def restore_user(user_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get("removed"):
        raise HTTPException(status_code=400, detail="Account is not removed")
    original_email = user.get("original_email")
    clash = await db.users.find_one({"email": original_email}, {"_id": 0})
    if clash and clash.get("user_id") != user_id:
        raise HTTPException(status_code=400, detail="That email has since been used by another account — cannot restore")
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {"email": original_email, "removed": False, "disabled": False},
            "$unset": {"removed_at": "", "removed_reason": "", "original_email": ""},
        }
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": None, "user_id": admin.user_id, "user_name": admin.name,
        "action": "user_restored", "entity_type": "user", "entity_id": user_id,
        "details": {}, "timestamp": now,
    })
    return {"ok": True}


@router.post("/users/{user_id}/delete")
async def delete_user_permanently(user_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Permanent deletion — the account row is removed entirely, immediately freeing the email."""
    confirm = data.get("confirm")
    if confirm != user_id:
        raise HTTPException(status_code=400, detail="Pass confirm=user_id to confirm deletion")
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.users.delete_one({"user_id": user_id})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": "platform", "user_id": admin.user_id, "user_name": admin.name,
        "action": "user_deleted_permanently", "entity_type": "user", "entity_id": user_id,
        "details": {"freed_email": user.get("original_email") or user.get("email")}, "timestamp": now,
    })
    return {"ok": True}


# ==================== FEATURE FLAGS (legacy simple store — superseded by /feature-flags below) ====================

@router.get("/feature-flags/legacy")
async def list_global_flags_legacy(_: CurrentUser = Depends(get_platform_admin)):
    """Legacy platform-wide feature flags (simple key-value store)"""
    flags = await db.feature_flags.find({"scope": "global"}, {"_id": 0}).to_list(200)
    return {"flags": flags, "total": len(flags)}


@router.put("/feature-flags/legacy/{flag_key}")
async def set_global_flag_legacy(flag_key: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
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


# ==================== PLATFORM AUDIT LOG (company-level — superseded by /audit-log below) ====================

@router.get("/company-audit-log")
async def platform_company_audit_log(
    limit: int = 100,
    action: Optional[str] = None,
    _: CurrentUser = Depends(get_platform_admin)
):
    """Company-level audit log across all tenants."""
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
    # Also log to emergency_actions
    await db.emergency_actions.insert_one({
        "action_id": f"emg_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action_type": "kill_switch_toggled",
        "reason": reason,
        "details": {"enabled": enabled},
        "created_at": now,
    })
    return {"kill_switch_enabled": enabled, "reason": reason}


# ===========================================================================
# PLATFORM OPERATORS MANAGEMENT
# ===========================================================================

PLATFORM_OPERATOR_ROLES = ["platform_owner", "platform_admin", "platform_support", "platform_billing", "platform_readonly"]


@router.get("/operators")
async def list_platform_operators(admin: CurrentUser = Depends(get_platform_admin)):
    """List all platform operators (super admin users)."""
    operators = await db.platform_operators.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"operators": operators, "total": len(operators)}


@router.post("/operators")
async def add_platform_operator(data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Add a new platform operator. Only platform_owner can do this."""
    if admin.role not in ("platform_owner",) and admin.email not in _get_platform_admin_emails():
        raise HTTPException(status_code=403, detail="Only platform owner can add operators")

    email = (data.get("email") or "").strip().lower()
    role = data.get("role", "platform_support")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    if role not in PLATFORM_OPERATOR_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(PLATFORM_OPERATOR_ROLES)}")

    # Find or note user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    user_id = user_doc["user_id"] if user_doc else email

    existing = await db.platform_operators.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="Operator with this email already exists")

    now = datetime.now(timezone.utc).isoformat()
    op = {
        "operator_id": f"op_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "email": email,
        "name": data.get("name", ""),
        "role": role,
        "is_active": True,
        "created_by": admin.email,
        "created_at": now,
        "updated_at": now,
    }
    await db.platform_operators.insert_one(op)

    # Update user record if exists
    if user_doc:
        await db.users.update_one({"email": email}, {"$set": {"is_platform_admin": True}})

    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "operator_added",
        "target_type": "platform_operator",
        "target_id": op["operator_id"],
        "details": {"email": email, "role": role},
        "created_at": now,
    })
    return {"message": "Platform operator added", "operator": op}


@router.patch("/operators/{operator_id}")
async def update_platform_operator(operator_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Update a platform operator's role or active status."""
    op = await db.platform_operators.find_one({"operator_id": operator_id}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "role" in data:
        if data["role"] not in PLATFORM_OPERATOR_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        updates["role"] = data["role"]
    if "is_active" in data:
        updates["is_active"] = bool(data["is_active"])

    await db.platform_operators.update_one({"operator_id": operator_id}, {"$set": updates})
    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "operator_updated",
        "target_type": "platform_operator",
        "target_id": operator_id,
        "details": updates,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Operator updated"}


@router.delete("/operators/{operator_id}")
async def remove_platform_operator(operator_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    """Remove a platform operator (deactivate, not delete)."""
    now = datetime.now(timezone.utc).isoformat()
    await db.platform_operators.update_one(
        {"operator_id": operator_id},
        {"$set": {"is_active": False, "updated_at": now}},
    )
    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "operator_removed",
        "target_type": "platform_operator",
        "target_id": operator_id,
        "details": {},
        "created_at": now,
    })
    return {"message": "Operator deactivated"}


# ===========================================================================
# PLATFORM FEATURE FLAGS
# ===========================================================================

DEFAULT_FEATURE_FLAGS = [
    {"flag_key": "ukvi_compliance_scanner", "display_name": "UKVI Compliance Scanner", "description": "Allow companies to run UKVI compliance scans"},
    {"flag_key": "ukvi_report_download", "display_name": "UKVI Report Download", "description": "Allow PDF/DOCX report downloads from compliance scans"},
    {"flag_key": "hmrc_rti", "display_name": "HMRC RTI", "description": "HMRC RTI FPS/EPS preparation and export; live transmission requires provider activation (see /super-admin/payroll-engine-status)"},
    {"flag_key": "payroll_processing", "display_name": "Payroll Processing", "description": "Full payroll and pay run processing"},
    {"flag_key": "payslip_paid_download", "display_name": "Payslip Paid Download", "description": "£5 per-payslip PDF download"},
    {"flag_key": "enterprise_multi_entity", "display_name": "Multi-Entity Support", "description": "Multi-company enterprise feature"},
    {"flag_key": "enterprise_sso", "display_name": "SSO/SAML", "description": "Enterprise SSO via SCIM/SAML"},
    {"flag_key": "ai_copilot", "display_name": "AI Copilot", "description": "AI assistant powered by Claude"},
]


@router.get("/feature-flags")
async def list_platform_feature_flags(admin: CurrentUser = Depends(get_platform_admin)):
    """Get all platform-level feature flags."""
    existing = {
        f["flag_key"]: f
        for f in await db.platform_feature_flags.find({}, {"_id": 0}).to_list(200)
    }
    result = []
    for default in DEFAULT_FEATURE_FLAGS:
        flag = existing.get(default["flag_key"], {})
        result.append({
            **default,
            "global_enabled": flag.get("global_enabled", True),
            "plan_rules_json": flag.get("plan_rules_json", {}),
            "company_overrides": flag.get("company_overrides", {}),
            "flag_id": flag.get("flag_id"),
            "updated_at": flag.get("updated_at"),
        })
    return {"flags": result}


@router.put("/feature-flags/{flag_key}")
async def update_platform_feature_flag(flag_key: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Update a platform feature flag. Can set global_enabled, plan_rules_json, company_overrides."""
    now = datetime.now(timezone.utc).isoformat()
    updates: dict = {"updated_at": now, "updated_by": admin.email}

    if "global_enabled" in data:
        updates["global_enabled"] = bool(data["global_enabled"])
    if "plan_rules_json" in data:
        updates["plan_rules_json"] = data["plan_rules_json"]
    if "company_overrides" in data:
        updates["company_overrides"] = data["company_overrides"]

    existing = await db.platform_feature_flags.find_one({"flag_key": flag_key}, {"_id": 0})
    if existing:
        await db.platform_feature_flags.update_one({"flag_key": flag_key}, {"$set": updates})
    else:
        desc = next((f["description"] for f in DEFAULT_FEATURE_FLAGS if f["flag_key"] == flag_key), "")
        updates.update({
            "flag_id": f"ff_{uuid.uuid4().hex[:12]}",
            "flag_key": flag_key,
            "display_name": flag_key.replace("_", " ").title(),
            "description": desc,
            "global_enabled": updates.get("global_enabled", True),
            "plan_rules_json": updates.get("plan_rules_json", {}),
            "company_overrides": updates.get("company_overrides", {}),
            "created_at": now,
        })
        await db.platform_feature_flags.insert_one(updates)

    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "feature_flag_updated",
        "target_type": "platform_feature_flag",
        "target_id": flag_key,
        "details": updates,
        "created_at": now,
    })
    return {"message": f"Feature flag '{flag_key}' updated"}


# ===========================================================================
# EMERGENCY ACTIONS
# ===========================================================================

@router.get("/emergency-actions")
async def list_emergency_actions(admin: CurrentUser = Depends(get_platform_admin)):
    """List recent emergency control actions."""
    actions = await db.emergency_actions.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"actions": actions, "total": len(actions)}


@router.post("/emergency/rti-freeze/{company_id}")
async def freeze_company_rti(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Freeze RTI submissions for a specific company (emergency control)."""
    reason = data.get("reason", "Emergency RTI freeze by platform admin")
    now = datetime.now(timezone.utc).isoformat()

    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"rti_frozen": True, "rti_frozen_reason": reason, "rti_frozen_at": now}},
    )
    await db.emergency_actions.insert_one({
        "action_id": f"emg_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action_type": "rti_freeze",
        "target_id": company_id,
        "reason": reason,
        "details": {},
        "created_at": now,
    })
    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "rti_freeze_applied",
        "target_type": "company",
        "target_id": company_id,
        "details": {"reason": reason},
        "created_at": now,
    })
    return {"message": f"RTI frozen for company {company_id}", "reason": reason}


@router.post("/emergency/rti-unfreeze/{company_id}")
async def unfreeze_company_rti(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Unfreeze RTI submissions for a company."""
    now = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"rti_frozen": False, "rti_frozen_reason": None}},
    )
    await db.platform_audit_logs.insert_one({
        "log_id": f"plog_{uuid.uuid4().hex[:12]}",
        "operator_id": admin.user_id,
        "operator_email": admin.email,
        "action": "rti_freeze_removed",
        "target_type": "company",
        "target_id": company_id,
        "details": {},
        "created_at": now,
    })
    return {"message": f"RTI unfrozen for company {company_id}"}


@router.post("/emergency/disable-ai/{company_id}")
async def disable_company_ai(company_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Disable AI Copilot for a specific company."""
    reason = data.get("reason", "AI disabled by platform admin")
    now = datetime.now(timezone.utc).isoformat()
    await db.feature_flags.update_one(
        {"company_id": company_id, "flag_name": "ai_copilot"},
        {"$set": {"enabled": False, "updated_at": now}},
        upsert=True,
    )
    await db.emergency_actions.insert_one({
        "action_id": f"emg_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action_type": "ai_disabled",
        "target_id": company_id,
        "reason": reason,
        "details": {},
        "created_at": now,
    })
    return {"message": f"AI Copilot disabled for company {company_id}"}


# ===========================================================================
# PLATFORM AUDIT LOG
# ===========================================================================

@router.get("/audit-log")
async def get_platform_audit_log(
    limit: int = 50,
    admin: CurrentUser = Depends(get_platform_admin),
):
    """Get the platform-wide audit log."""
    logs = await db.platform_audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"logs": logs, "total": len(logs)}


# ===========================================================================
# USER MANAGEMENT — RESET MFA / FORCE LOGOUT
# ===========================================================================

@router.post("/users/{user_id}/reset-mfa")
async def reset_user_mfa(
    user_id: str,
    admin: CurrentUser = Depends(get_platform_admin),
):
    """
    Reset 2FA/MFA for a specific user. Clears TOTP secret and backup codes.
    User will be prompted to re-enroll on next login.
    """
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "totp_enabled": False,
            "totp_secret": None,
            "totp_backup_codes": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    await db.platform_audit_logs.insert_one({
        "log_id": f"pal_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action": "reset_user_mfa",
        "target_type": "user",
        "target_id": user_id,
        "details": {"user_email": user.get("email")},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"message": f"2FA reset for user {user_id}. They will need to re-enroll on next login."}


@router.post("/users/{user_id}/force-logout")
async def force_logout_user(
    user_id: str,
    admin: CurrentUser = Depends(get_platform_admin),
):
    """
    Force logout a user by incrementing their token_version.
    All existing JWT tokens for this user will become invalid.
    """
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_version = (user.get("token_version") or 0) + 1
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "token_version": new_version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    await db.platform_audit_logs.insert_one({
        "log_id": f"pal_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action": "force_logout_user",
        "target_type": "user",
        "target_id": user_id,
        "details": {"user_email": user.get("email"), "new_token_version": new_version},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"message": f"User {user_id} has been force-logged out. All active sessions are now invalid."}


# ===========================================================================
# PLATFORM SECURITY SETTINGS
# ===========================================================================

SECURITY_SETTINGS_KEY = "platform_security_settings"

DEFAULT_SECURITY_SETTINGS = {
    "mfa_enforcement": "optional",      # optional | required_for_admins | required_for_all
    "session_timeout_hours": 24,
    "max_sessions_per_user": 5,
    "ip_allowlist_enabled": False,
    "ip_allowlist": [],
    "login_attempt_lockout": 10,
    "password_min_length": 8,
    "require_uppercase": True,
    "require_special_char": True,
    "platform_admin_emails": [],
}


@router.get("/security/settings")
async def get_security_settings(admin: CurrentUser = Depends(get_platform_admin)):
    """Get platform-wide security policy settings."""
    doc = await db.platform_settings.find_one({"key": SECURITY_SETTINGS_KEY}, {"_id": 0})
    settings = {**DEFAULT_SECURITY_SETTINGS, **(doc.get("settings") if doc else {})}
    # Merge designated admin emails from env
    env_emails = _get_platform_admin_emails()
    # Also pull is_platform_admin users
    db_admins = await db.users.find(
        {"is_platform_admin": True},
        {"_id": 0, "email": 1, "name": 1, "totp_enabled": 1}
    ).to_list(100)
    designated_admins = [
        {"email": u.get("email"), "name": u.get("name", ""), "mfa_active": bool(u.get("totp_enabled"))}
        for u in db_admins
    ]
    # Include env-only admins not yet in DB
    db_emails = {u.get("email") for u in db_admins}
    for e in env_emails:
        if e not in db_emails:
            designated_admins.append({"email": e, "name": "(env only)", "mfa_active": False})

    return {"settings": settings, "designated_admins": designated_admins}


@router.put("/security/settings")
async def update_security_settings(data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Update platform-wide security policy settings."""
    allowed_keys = set(DEFAULT_SECURITY_SETTINGS.keys())
    updates = {k: v for k, v in data.items() if k in allowed_keys}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    now = datetime.now(timezone.utc).isoformat()
    await db.platform_settings.update_one(
        {"key": SECURITY_SETTINGS_KEY},
        {"$set": {"key": SECURITY_SETTINGS_KEY, "settings": updates, "updated_at": now, "updated_by": admin.email}},
        upsert=True,
    )
    await db.platform_audit_logs.insert_one({
        "log_id": f"pal_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action": "security_settings_updated",
        "target_type": "platform_settings",
        "target_id": SECURITY_SETTINGS_KEY,
        "details": updates,
        "created_at": now,
    })
    return {"message": "Security settings updated", "updated": updates}


@router.post("/security/revoke-all-sessions")
async def revoke_all_sessions(data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Revoke all active user sessions across the platform (emergency use)."""
    reason = data.get("reason", "Security policy enforcement")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.user_sessions.delete_many({})
    await db.platform_audit_logs.insert_one({
        "log_id": f"pal_{uuid.uuid4().hex[:12]}",
        "operator_email": admin.email,
        "action": "all_sessions_revoked",
        "target_type": "platform",
        "target_id": "all_sessions",
        "details": {"reason": reason, "sessions_deleted": result.deleted_count},
        "created_at": now,
    })
    return {"message": f"Revoked {result.deleted_count} active sessions", "reason": reason}


# ===========================================================================
# SYSTEM HEALTH
# ===========================================================================

@router.get("/system/health")
async def get_system_health(admin: CurrentUser = Depends(get_platform_admin)):
    """Aggregate real-time platform health indicators."""
    now = datetime.now(timezone.utc)

    # RTI submissions
    pending_rti = await db.rti_submissions.count_documents({"status": {"$in": ["pending", "prepared", "approved"]}})
    failed_rti = await db.rti_submissions.count_documents({"status": "failed"})
    last_rti = await db.rti_submissions.find_one({}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])

    # Notifications / email queue proxy
    pending_notifications = await db.notifications.count_documents({"read": False})

    # Compliance alerts
    open_alerts = await db.ukvi_compliance_alerts.count_documents({"status": "open"})

    # Active sessions
    active_sessions = await db.user_sessions.count_documents({})

    # Platform audit log — last 24h events
    cutoff_24h = (now - timedelta(hours=24)).isoformat()
    audit_24h = await db.platform_audit_logs.count_documents({"created_at": {"$gt": cutoff_24h}})

    # Recent RTI submissions in last 7 days
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    rti_7d = await db.rti_submissions.count_documents({"created_at": {"$gt": cutoff_7d}})

    # Companies
    total_companies = await db.companies.count_documents({})
    active_companies = await db.companies.count_documents({"suspended": {"$ne": True}})

    return {
        "timestamp": now.isoformat(),
        "services": {
            "database": {"status": "healthy", "note": "MongoDB connection active"},
            "rti_queue": {
                "status": "warning" if failed_rti > 0 else "healthy",
                "pending": pending_rti,
                "failed": failed_rti,
                "processed_last_7d": rti_7d,
                "last_activity": last_rti.get("created_at") if last_rti else None,
            },
            "email_queue": {
                "status": "healthy",
                "pending_notifications": pending_notifications,
                "note": "Resend integration — notifications counted",
            },
            "compliance_engine": {
                "status": "warning" if open_alerts > 5 else "healthy",
                "open_alerts": open_alerts,
            },
            "ai_copilot": {
                "status": "healthy",
                "note": "Claude API via Anthropic",
            },
            "file_storage": {
                "status": "healthy",
                "note": "Document storage operational",
            },
        },
        "platform": {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "active_sessions": active_sessions,
            "audit_events_24h": audit_24h,
        },
    }


@router.get("/payroll-engine-status")
async def get_platform_payroll_engine_status(admin: CurrentUser = Depends(get_platform_admin)):
    """
    Platform-wide payroll/RTI/pension engine status.

    Live HMRC RTI submission and pension provider integration are disabled
    platform-wide until a real embedded payroll provider or HMRC Gateway
    integration is connected and explicitly enabled.
    """
    from feature_flags import get_all_flags
    from services.rti_sync_service import rti_sync_engine

    flags = await get_all_flags()

    total_simulated = await db.rti_submissions.count_documents({"is_simulated": True})
    total_live = await db.rti_receipts.count_documents({"is_simulated": False})
    total_legacy_blocked = await db.audit_log.count_documents({"action": "legacy_hmrc_submission_blocked"})

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
        "current_mode": current_mode,
        "totals": {
            "simulated_rti_submissions": total_simulated,
            "live_rti_submissions": total_live,
            "legacy_hmrc_attempts_blocked": total_legacy_blocked,
        },
    }


# ===========================================================================
# DISCOUNT / PROMO CODES
# ===========================================================================

# ===========================================================================
# EMAIL TEMPLATES — platform owner can edit and preview welcome email
# ===========================================================================

@router.get("/email-templates/{template_id}")
async def get_email_template(template_id: str, _: CurrentUser = Depends(get_platform_admin)):
    """Return the stored email template, or the built-in default if never saved."""
    doc = await db.email_templates.find_one({"template_id": template_id}, {"_id": 0})
    if doc:
        doc["is_default"] = False
        return doc
    from services.email_service import get_default_welcome_template
    return get_default_welcome_template()


@router.put("/email-templates/{template_id}")
async def update_email_template(template_id: str, data: dict, admin: CurrentUser = Depends(get_platform_admin)):
    """Save edited email template to DB."""
    now = datetime.now(timezone.utc).isoformat()
    await db.email_templates.update_one(
        {"template_id": template_id},
        {"$set": {
            "template_id": template_id,
            "subject": data.get("subject", ""),
            "html_body": data.get("html_body", ""),
            "from_name": data.get("from_name", "RealtouchHR"),
            "from_email": data.get("from_email", ""),
            "updated_at": now,
            "updated_by": admin.email,
        }},
        upsert=True,
    )
    return {"status": "saved", "updated_at": now}


@router.post("/email-templates/{template_id}/reset")
async def reset_email_template(template_id: str, _: CurrentUser = Depends(get_platform_admin)):
    """Delete the stored template so the built-in default is used again."""
    await db.email_templates.delete_one({"template_id": template_id})
    return {"status": "reset"}


@router.post("/email-templates/{template_id}/send-test")
async def send_test_welcome_email(template_id: str, admin: CurrentUser = Depends(get_platform_admin)):
    """Send the current template (saved or default) to the admin's own email address."""
    from services.email_service import (
        email_service, get_default_welcome_template, render_welcome_email,
    )
    doc = await db.email_templates.find_one({"template_id": template_id}, {"_id": 0})
    if doc:
        subject = doc["subject"]
        html = render_welcome_email(doc["html_body"], admin.name or "Admin", "RealtouchHR (Test)")
    else:
        tpl = get_default_welcome_template()
        subject = tpl["subject"]
        html = render_welcome_email(tpl["html_body"], admin.name or "Admin", "RealtouchHR (Test)")

    result = await email_service.send_email(admin.email, f"[TEST] {subject}", html)
    if result.get("mock"):
        return {"status": "mock", "message": "Email service in mock mode — set RESEND_API_KEY to send real emails", "to": admin.email}
    if result.get("success"):
        return {"status": "sent", "to": admin.email, "message_id": result.get("message_id")}
    return {"status": "failed", "error": result.get("error", "Unknown error")}


@router.get("/discount-codes")
async def get_discount_code_usage(_: CurrentUser = Depends(get_platform_admin)):
    """Return all promotional discount code usage records."""
    try:
        usages = await db.promo_code_usage.find({}, {"_id": 0}).to_list(2000)
        usages_sorted = sorted(usages, key=lambda x: x.get("applied_at", ""), reverse=True)
    except Exception:
        usages_sorted = []
    # Summary per code
    summary: dict = {}
    for u in usages_sorted:
        code = u.get("code", "")
        if code not in summary:
            summary[code] = {"code": code, "total_uses": 0, "discount_percent": u.get("discount_percent"), "months": u.get("months")}
        summary[code]["total_uses"] += 1
    return {
        "usages": usages_sorted,
        "summary": list(summary.values()),
    }
