"""
RealtouchHR - Policies Module
Policy library + assign-to-staff + acknowledgement tracking + version control + review reminders
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
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

router = APIRouter(prefix="/policies", tags=["Policies"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None

    class Config:
        extra = "ignore"


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


def _hr_only(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="HR/Admin only")


class PolicyCreate(BaseModel):
    title: str
    category: str = Field("general", description="general | safeguarding | data_protection | equality | health_safety | disciplinary | grievance | absence | remote_working | whistleblowing | rtw | other")
    content: Optional[str] = None
    file_url: Optional[str] = None
    review_date: Optional[str] = None
    mandatory: bool = True


@router.post("")
async def create_policy(data: PolicyCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    now = datetime.now(timezone.utc)
    pid = f"pol_{uuid.uuid4().hex[:12]}"
    doc = {
        "policy_id": pid,
        "company_id": user.company_id,
        "title": data.title,
        "category": data.category,
        "content": data.content,
        "file_url": data.file_url,
        "version": 1,
        "status": "active",
        "review_date": data.review_date,
        "mandatory": data.mandatory,
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.policies.insert_one(dict(doc))
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id, "user_id": user.user_id, "user_name": user.name,
        "action": "policy.create", "entity_type": "policy", "entity_id": pid,
        "details": {"title": data.title}, "timestamp": now.isoformat()
    })
    return doc


@router.get("")
async def list_policies(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    docs = await db.policies.find({"company_id": user.company_id}, {"_id": 0}).sort("created_at", -1).to_list(length=500)
    return {"policies": docs}


@router.put("/{policy_id}")
async def update_policy(policy_id: str, data: PolicyCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    existing = await db.policies.find_one({"policy_id": policy_id, "company_id": user.company_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    now = datetime.now(timezone.utc)
    new_version = existing.get("version", 1) + 1
    # Archive previous version
    await db.policy_versions.insert_one({
        "policy_id": policy_id, "version": existing.get("version", 1),
        "snapshot": {k: v for k, v in existing.items() if k != "_id"},
        "archived_at": now.isoformat()
    })
    update_fields = {
        "title": data.title, "category": data.category, "content": data.content,
        "file_url": data.file_url, "review_date": data.review_date, "mandatory": data.mandatory,
        "version": new_version, "updated_at": now.isoformat(), "updated_by": user.user_id
    }
    await db.policies.update_one({"policy_id": policy_id}, {"$set": update_fields})
    # Bumping version invalidates previous acknowledgements
    await db.policy_acknowledgements.update_many(
        {"policy_id": policy_id, "version": {"$lt": new_version}},
        {"$set": {"superseded": True}}
    )
    return {"ok": True, "version": new_version}


@router.delete("/{policy_id}")
async def archive_policy(policy_id: str, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    res = await db.policies.update_one(
        {"policy_id": policy_id, "company_id": user.company_id},
        {"$set": {"status": "archived", "archived_at": datetime.now(timezone.utc).isoformat()}}
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/{policy_id}/assign")
async def assign_policy(policy_id: str, body: dict, user: CurrentUser = Depends(get_current_user)):
    """Body: {employee_ids: [...]} — assigns acknowledgement requirement to listed employees."""
    _hr_only(user)
    policy = await db.policies.find_one({"policy_id": policy_id, "company_id": user.company_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    employee_ids = body.get("employee_ids") or []
    assigned = 0
    now = datetime.now(timezone.utc)
    for eid in employee_ids:
        existing = await db.policy_acknowledgements.find_one({
            "policy_id": policy_id, "employee_id": eid, "version": policy.get("version", 1)
        }, {"_id": 0})
        if existing:
            continue
        await db.policy_acknowledgements.insert_one({
            "ack_id": f"ack_{uuid.uuid4().hex[:12]}",
            "policy_id": policy_id, "employee_id": eid,
            "company_id": user.company_id,
            "version": policy.get("version", 1),
            "status": "pending",
            "assigned_at": now.isoformat(),
            "acknowledged_at": None,
            "superseded": False
        })
        assigned += 1
    return {"ok": True, "assigned": assigned}


@router.post("/{policy_id}/acknowledge")
async def acknowledge_policy(policy_id: str, user: CurrentUser = Depends(get_current_user)):
    """Employee acknowledges a policy. Self-service."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    policy = await db.policies.find_one({"policy_id": policy_id, "company_id": user.company_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    # Match by user's employee_id if linked, else by email
    emp = await db.employees.find_one({"$or": [{"email": user.email}, {"user_id": user.user_id}], "company_id": user.company_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="No linked employee record")
    now = datetime.now(timezone.utc).isoformat()
    upd = await db.policy_acknowledgements.update_one(
        {"policy_id": policy_id, "employee_id": emp["employee_id"], "version": policy.get("version", 1)},
        {"$set": {"status": "acknowledged", "acknowledged_at": now}},
        upsert=True
    )
    return {"ok": True, "acknowledged_at": now}


@router.get("/{policy_id}/acknowledgements")
async def list_acknowledgements(policy_id: str, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    docs = await db.policy_acknowledgements.find(
        {"policy_id": policy_id, "company_id": user.company_id}, {"_id": 0}
    ).to_list(length=2000)
    return {"acknowledgements": docs}


@router.get("/my/pending")
async def my_pending(user: CurrentUser = Depends(get_current_user)):
    """Employee self-service: list policies assigned to me with pending acknowledgement."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    emp = await db.employees.find_one({"$or": [{"email": user.email}, {"user_id": user.user_id}], "company_id": user.company_id}, {"_id": 0})
    if not emp:
        return {"pending": []}
    acks = await db.policy_acknowledgements.find(
        {"employee_id": emp["employee_id"], "company_id": user.company_id, "status": "pending", "superseded": {"$ne": True}}, {"_id": 0}
    ).to_list(length=200)
    pids = [a["policy_id"] for a in acks]
    if not pids:
        return {"pending": []}
    policies = await db.policies.find({"policy_id": {"$in": pids}}, {"_id": 0}).to_list(length=200)
    return {"pending": policies, "acknowledgements": acks}
