"""
RealtouchHR - Absence & Sickness Module
Distinct from Leave. Tracks sickness, fit notes, return-to-work interviews, Bradford factor.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta, date
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

router = APIRouter(prefix="/absence", tags=["Absence & Sickness"])


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


class AbsenceCreate(BaseModel):
    employee_id: str
    start_date: str
    end_date: str
    reason: str = "sickness"  # sickness | injury | medical_appointment | bereavement | other
    description: Optional[str] = None
    fit_note_url: Optional[str] = None
    self_certified: bool = True


def _days_inclusive(start: str, end: str) -> int:
    try:
        s = datetime.fromisoformat(start).date()
        e = datetime.fromisoformat(end).date()
        return max(1, (e - s).days + 1)
    except Exception:
        return 1


@router.post("")
async def create_absence(data: AbsenceCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    aid = f"abs_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    duration = _days_inclusive(data.start_date, data.end_date)
    doc = {
        "absence_id": aid, "company_id": user.company_id,
        "employee_id": data.employee_id, "start_date": data.start_date, "end_date": data.end_date,
        "duration_days": duration, "reason": data.reason, "description": data.description,
        "fit_note_url": data.fit_note_url, "self_certified": data.self_certified,
        "return_to_work_done": False, "return_to_work_notes": None,
        "created_at": now, "created_by": user.user_id
    }
    await db.absence_records.insert_one(dict(doc))
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id, "user_id": user.user_id, "user_name": user.name,
        "action": "absence.create", "entity_type": "absence", "entity_id": aid,
        "details": {"employee_id": data.employee_id, "duration_days": duration}, "timestamp": now
    })
    return doc


@router.get("")
async def list_absences(employee_id: Optional[str] = None, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    q = {"company_id": user.company_id}
    if employee_id:
        q["employee_id"] = employee_id
    docs = await db.absence_records.find(q, {"_id": 0}).sort("start_date", -1).to_list(length=2000)
    return {"absences": docs}


class ReturnToWorkBody(BaseModel):
    notes: str


@router.post("/{absence_id}/return-to-work")
async def return_to_work(absence_id: str, body: ReturnToWorkBody, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    res = await db.absence_records.update_one(
        {"absence_id": absence_id, "company_id": user.company_id},
        {"$set": {
            "return_to_work_done": True, "return_to_work_notes": body.notes,
            "return_to_work_by": user.user_id,
            "return_to_work_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.get("/bradford")
async def bradford_scores(year: Optional[int] = None, user: CurrentUser = Depends(get_current_user)):
    """
    Bradford Factor = S^2 * D over rolling 12 months (or calendar year).
      S = number of separate absence episodes
      D = total days absent
    Returns one row per employee.
    """
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    if year is None:
        # rolling 12 months
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
        q = {"company_id": user.company_id, "start_date": {"$gte": cutoff}, "reason": "sickness"}
    else:
        q = {"company_id": user.company_id,
             "start_date": {"$gte": f"{year}-01-01", "$lt": f"{year+1}-01-01"},
             "reason": "sickness"}
    records = await db.absence_records.find(q, {"_id": 0}).to_list(length=10000)
    by_emp = {}
    for r in records:
        eid = r["employee_id"]
        by_emp.setdefault(eid, {"episodes": 0, "days": 0})
        by_emp[eid]["episodes"] += 1
        by_emp[eid]["days"] += r.get("duration_days", 1)
    out = []
    for eid, agg in by_emp.items():
        s = agg["episodes"]
        d = agg["days"]
        score = (s * s) * d
        risk = "low"
        if score >= 200:
            risk = "high"
        elif score >= 50:
            risk = "medium"
        out.append({"employee_id": eid, "episodes": s, "days": d, "bradford_score": score, "risk": risk})
    out.sort(key=lambda x: x["bradford_score"], reverse=True)
    return {"period": ("year=" + str(year)) if year else "rolling_12_months", "results": out}
