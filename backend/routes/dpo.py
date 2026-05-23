"""
RealtouchHR - Data Protection Centre Extensions
Article 30 data processing activities, DSAR tracker, breach incident register, processor register,
retention schedule, DPIA records — all required by UK GDPR / Data Protection Act 2018.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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

router = APIRouter(prefix="/dpo", tags=["Data Protection Centre"])


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


def _hr_or_admin(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager", "compliance_officer"):
        raise HTTPException(status_code=403, detail="HR/Admin only")


def _audit(coll_name: str, action: str, user: CurrentUser, entity_id: str, details: dict):
    """Fire-and-forget audit entry. Caller doesn't await — runs in background."""
    pass  # We do inline await below for simplicity


# =========================================================
#  DATA PROCESSING ACTIVITIES (Article 30)
# =========================================================

class DPACreate(BaseModel):
    activity_name: str
    purpose: str
    legal_basis: str  # consent | contract | legal_obligation | vital_interests | public_task | legitimate_interests
    data_categories: List[str] = []
    data_subjects: List[str] = []  # employees | candidates | sponsored_workers | customers ...
    retention_period: Optional[str] = None
    recipients: List[str] = []
    third_country_transfers: Optional[str] = None
    security_measures: Optional[str] = None


@router.post("/processing-activities")
async def create_dpa(data: DPACreate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    aid = f"dpa_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {"dpa_id": aid, "company_id": user.company_id, **data.dict(),
           "created_at": now, "created_by": user.user_id, "updated_at": now}
    await db.data_processing_activities.insert_one(dict(doc))
    return doc


@router.get("/processing-activities")
async def list_dpas(user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    docs = await db.data_processing_activities.find({"company_id": user.company_id}, {"_id": 0}).sort("created_at", -1).to_list(length=200)
    return {"activities": docs}


@router.delete("/processing-activities/{dpa_id}")
async def delete_dpa(dpa_id: str, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    await db.data_processing_activities.delete_one({"dpa_id": dpa_id, "company_id": user.company_id})
    return {"ok": True}


# =========================================================
#  DSAR (Data Subject Access Request) TRACKER
# =========================================================
# Note: The actual fulfilment uses /api/gdpr/my-data. This tracker logs DSARs from
# data subjects so HR can prove they responded within the statutory 30-day window.

class DSARCreate(BaseModel):
    subject_email: str
    subject_name: Optional[str] = None
    request_type: str = "access"  # access | rectification | erasure | portability | restriction | objection
    description: Optional[str] = None


@router.post("/dsar")
async def create_dsar(data: DSARCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    rid = f"dsar_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(days=30)).isoformat()
    doc = {
        "dsar_id": rid, "company_id": user.company_id,
        "subject_email": data.subject_email, "subject_name": data.subject_name,
        "request_type": data.request_type, "description": data.description,
        "status": "open", "received_at": now.isoformat(),
        "deadline_at": deadline, "completed_at": None,
        "logged_by": user.user_id,
    }
    await db.dsar_requests.insert_one(dict(doc))
    return doc


@router.get("/dsar")
async def list_dsars(status: Optional[str] = None, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    q = {"company_id": user.company_id}
    if status:
        q["status"] = status
    docs = await db.dsar_requests.find(q, {"_id": 0}).sort("received_at", -1).to_list(length=500)
    today = datetime.now(timezone.utc).date()
    for d in docs:
        try:
            dl = datetime.fromisoformat(d["deadline_at"]).date()
            d["days_to_deadline"] = (dl - today).days
            d["overdue"] = d["status"] == "open" and d["days_to_deadline"] < 0
        except Exception:
            d["days_to_deadline"] = None
            d["overdue"] = False
    return {"requests": docs}


class DSARUpdate(BaseModel):
    status: str  # open | in_progress | completed | rejected
    response_notes: Optional[str] = None


@router.post("/dsar/{dsar_id}/update")
async def update_dsar(dsar_id: str, body: DSARUpdate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    update_fields: Dict[str, Any] = {
        "status": body.status,
        "response_notes": body.response_notes,
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_by": user.user_id,
    }
    if body.status in ("completed", "rejected"):
        update_fields["completed_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.dsar_requests.update_one(
        {"dsar_id": dsar_id, "company_id": user.company_id},
        {"$set": update_fields}
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="DSAR not found")
    return {"ok": True}


# =========================================================
#  BREACH INCIDENT REGISTER
# =========================================================

class BreachCreate(BaseModel):
    title: str
    description: str
    severity: str = "medium"  # low | medium | high | critical
    affected_data_subjects: Optional[int] = None
    affected_data_categories: List[str] = []
    discovered_at: str
    ico_notified: bool = False
    ico_notification_date: Optional[str] = None
    individuals_notified: bool = False
    mitigation_steps: Optional[str] = None


@router.post("/breaches")
async def create_breach(data: BreachCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    bid = f"brch_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    # ICO 72-hour deadline calculator
    try:
        disc = datetime.fromisoformat(data.discovered_at.replace("Z", "+00:00"))
        ico_deadline = (disc + timedelta(hours=72)).isoformat()
    except Exception:
        ico_deadline = None
    doc = {"breach_id": bid, "company_id": user.company_id, **data.dict(),
           "ico_72h_deadline": ico_deadline, "status": "open",
           "logged_at": now, "logged_by": user.user_id}
    await db.breach_incidents.insert_one(dict(doc))
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id, "user_id": user.user_id, "user_name": user.name,
        "action": "breach.create", "entity_type": "breach", "entity_id": bid,
        "details": {"severity": data.severity}, "timestamp": now
    })
    return doc


@router.get("/breaches")
async def list_breaches(user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    docs = await db.breach_incidents.find({"company_id": user.company_id}, {"_id": 0}).sort("logged_at", -1).to_list(length=500)
    return {"breaches": docs}


@router.post("/breaches/{breach_id}/close")
async def close_breach(breach_id: str, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    res = await db.breach_incidents.update_one(
        {"breach_id": breach_id, "company_id": user.company_id},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat(), "closed_by": user.user_id}}
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# =========================================================
#  PROCESSORS / SUB-PROCESSORS REGISTER
# =========================================================

class ProcessorCreate(BaseModel):
    name: str
    purpose: str
    country: Optional[str] = None
    contact_email: Optional[str] = None
    data_categories: List[str] = []
    dpa_signed: bool = False
    dpa_signed_date: Optional[str] = None
    sub_processors: List[str] = []
    notes: Optional[str] = None


@router.post("/processors")
async def create_processor(data: ProcessorCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    pid = f"proc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {"processor_id": pid, "company_id": user.company_id, **data.dict(),
           "created_at": now, "created_by": user.user_id}
    await db.processors_register.insert_one(dict(doc))
    return doc


@router.get("/processors")
async def list_processors(user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    docs = await db.processors_register.find({"company_id": user.company_id}, {"_id": 0}).sort("name", 1).to_list(length=500)
    return {"processors": docs}


@router.delete("/processors/{processor_id}")
async def delete_processor(processor_id: str, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    await db.processors_register.delete_one({"processor_id": processor_id, "company_id": user.company_id})
    return {"ok": True}


# =========================================================
#  RETENTION SCHEDULE
# =========================================================

@router.get("/retention-schedule")
async def get_retention_schedule(user: CurrentUser = Depends(get_current_user)):
    """
    Default retention schedule based on UK statutory minimums.
    Companies can override via /override below.
    """
    _hr_or_admin(user)
    defaults = [
        {"category": "Payroll records (RTI submissions, payslips)", "retention": "6 years from end of tax year", "basis": "HMRC PAYE / Finance Act"},
        {"category": "Employee personal data (after leaving)", "retention": "6 years", "basis": "Limitation Act 1980 (employment claims)"},
        {"category": "Right-to-Work check evidence", "retention": "2 years after employment ends", "basis": "Section 15 Immigration, Asylum & Nationality Act 2006"},
        {"category": "Sponsor Licence records (CoS, monitoring)", "retention": "Duration of sponsorship + 1 year", "basis": "Workers and Temporary Workers: guidance for sponsors"},
        {"category": "Pension scheme records", "retention": "6 years", "basis": "Pensions Regulator guidance"},
        {"category": "Audit logs", "retention": "7 years", "basis": "UK DPA 2018 accountability principle"},
        {"category": "Sickness records (incl. fit notes)", "retention": "3 years (4 weeks if SSP)", "basis": "Statutory Sick Pay (General) Regulations 1982"},
        {"category": "Recruitment data (unsuccessful candidates)", "retention": "6 months", "basis": "ICO guidance"},
        {"category": "Working time records", "retention": "2 years", "basis": "Working Time Regulations 1998"},
        {"category": "Performance reviews", "retention": "6 years after employment ends", "basis": "Limitation Act 1980"},
        {"category": "Disciplinary / grievance records", "retention": "6 years after closed", "basis": "ACAS code + Limitation Act 1980"},
        {"category": "Health and safety incident records", "retention": "3 years", "basis": "RIDDOR / HSE"},
    ]
    overrides = await db.retention_overrides.find({"company_id": user.company_id}, {"_id": 0}).to_list(length=100)
    return {"defaults": defaults, "overrides": overrides}


class RetentionOverride(BaseModel):
    category: str
    custom_retention: str
    reason: str


@router.post("/retention-schedule/override")
async def add_override(data: RetentionOverride, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    oid = f"ret_{uuid.uuid4().hex[:12]}"
    doc = {"override_id": oid, "company_id": user.company_id, **data.dict(),
           "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user.user_id}
    await db.retention_overrides.insert_one(dict(doc))
    return doc


# =========================================================
#  DPIA RECORDS (Data Protection Impact Assessment)
# =========================================================

class DPIACreate(BaseModel):
    project_name: str
    description: str
    risk_level: str  # low | medium | high
    risks_identified: List[str] = []
    mitigation_measures: List[str] = []
    consultation_required: bool = False
    approved: bool = False


@router.post("/dpia")
async def create_dpia(data: DPIACreate, user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    did = f"dpia_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {"dpia_id": did, "company_id": user.company_id, **data.dict(),
           "created_at": now, "created_by": user.user_id}
    await db.dpia_records.insert_one(dict(doc))
    return doc


@router.get("/dpia")
async def list_dpias(user: CurrentUser = Depends(get_current_user)):
    _hr_or_admin(user)
    docs = await db.dpia_records.find({"company_id": user.company_id}, {"_id": 0}).sort("created_at", -1).to_list(length=200)
    return {"dpias": docs}
