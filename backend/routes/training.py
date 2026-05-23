"""
RealtouchHR - Training Records Module
Training course assignments, completion tracking, certificate uploads, renewal reminders, training matrix.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
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

router = APIRouter(prefix="/training", tags=["Training"])


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


class CourseCreate(BaseModel):
    title: str
    provider: Optional[str] = None
    description: Optional[str] = None
    mandatory: bool = False
    duration_hours: Optional[float] = None
    renewal_months: Optional[int] = None  # 0/None = no renewal needed


@router.post("/courses")
async def create_course(data: CourseCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    cid = f"course_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "course_id": cid, "company_id": user.company_id,
        "title": data.title, "provider": data.provider,
        "description": data.description, "mandatory": data.mandatory,
        "duration_hours": data.duration_hours, "renewal_months": data.renewal_months,
        "created_at": now, "created_by": user.user_id
    }
    await db.training_courses.insert_one(dict(doc))
    return doc


@router.get("/courses")
async def list_courses(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    docs = await db.training_courses.find({"company_id": user.company_id}, {"_id": 0}).sort("created_at", -1).to_list(length=500)
    return {"courses": docs}


class TrainingRecordCreate(BaseModel):
    course_id: str
    employee_id: str
    completion_date: Optional[str] = None
    certificate_url: Optional[str] = None
    status: str = "assigned"  # assigned | in_progress | completed | expired
    notes: Optional[str] = None


@router.post("/records")
async def create_record(data: TrainingRecordCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    course = await db.training_courses.find_one({"course_id": data.course_id, "company_id": user.company_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    expiry = None
    if data.completion_date and course.get("renewal_months"):
        try:
            from dateutil.relativedelta import relativedelta
            dt = datetime.fromisoformat(data.completion_date.replace("Z", "+00:00"))
            expiry = (dt + relativedelta(months=course["renewal_months"])).date().isoformat()
        except Exception:
            pass

    rid = f"train_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    rec = {
        "record_id": rid, "company_id": user.company_id,
        "course_id": data.course_id, "course_title": course.get("title"),
        "employee_id": data.employee_id,
        "completion_date": data.completion_date, "certificate_url": data.certificate_url,
        "expiry_date": expiry, "status": data.status, "notes": data.notes,
        "created_at": now, "created_by": user.user_id
    }
    await db.training_records.insert_one(dict(rec))
    return rec


@router.get("/records")
async def list_records(employee_id: Optional[str] = None, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    q = {"company_id": user.company_id}
    if employee_id:
        q["employee_id"] = employee_id
    docs = await db.training_records.find(q, {"_id": 0}).sort("created_at", -1).to_list(length=1000)
    return {"records": docs}


@router.put("/records/{record_id}")
async def update_record(record_id: str, data: TrainingRecordCreate, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    course = await db.training_courses.find_one({"course_id": data.course_id, "company_id": user.company_id}, {"_id": 0})
    expiry = None
    if data.completion_date and course and course.get("renewal_months"):
        try:
            from dateutil.relativedelta import relativedelta
            dt = datetime.fromisoformat(data.completion_date.replace("Z", "+00:00"))
            expiry = (dt + relativedelta(months=course["renewal_months"])).date().isoformat()
        except Exception:
            pass
    res = await db.training_records.update_one(
        {"record_id": record_id, "company_id": user.company_id},
        {"$set": {
            "course_id": data.course_id,
            "employee_id": data.employee_id,
            "completion_date": data.completion_date,
            "certificate_url": data.certificate_url,
            "expiry_date": expiry,
            "status": data.status,
            "notes": data.notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.get("/matrix")
async def training_matrix(user: CurrentUser = Depends(get_current_user)):
    """Returns the training matrix: rows = employees, columns = courses, cell = latest status."""
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}).to_list(length=2000)
    courses = await db.training_courses.find({"company_id": user.company_id}, {"_id": 0}).to_list(length=500)
    records = await db.training_records.find({"company_id": user.company_id}, {"_id": 0}).sort("created_at", -1).to_list(length=10000)
    # Build (employee_id, course_id) → latest record
    grid = {}
    for r in records:
        key = (r["employee_id"], r["course_id"])
        if key not in grid:
            grid[key] = r
    matrix = []
    today = datetime.now(timezone.utc).date()
    for emp in employees:
        row = {"employee_id": emp["employee_id"], "name": f"{emp.get('first_name','')} {emp.get('last_name','')}".strip(), "department": emp.get("department"), "courses": {}}
        for c in courses:
            r = grid.get((emp["employee_id"], c["course_id"]))
            if not r:
                row["courses"][c["course_id"]] = {"status": "not_started"}
            else:
                exp = r.get("expiry_date")
                status = r.get("status")
                if exp:
                    try:
                        d = datetime.fromisoformat(exp).date()
                        if d < today:
                            status = "expired"
                        elif (d - today).days < 60:
                            status = "expiring_soon"
                    except Exception:
                        pass
                row["courses"][c["course_id"]] = {"status": status, "expiry_date": exp, "completion_date": r.get("completion_date")}
        matrix.append(row)
    return {"courses": courses, "matrix": matrix}


@router.get("/expiring")
async def expiring_records(days: int = 60, user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    today = datetime.now(timezone.utc).date()
    cutoff = (today + timedelta(days=days)).isoformat()
    docs = await db.training_records.find(
        {"company_id": user.company_id, "expiry_date": {"$lte": cutoff, "$ne": None}},
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(length=1000)
    return {"records": docs, "today": today.isoformat(), "cutoff": cutoff}


@router.get("/my")
async def my_training(user: CurrentUser = Depends(get_current_user)):
    """Employee self-service training view."""
    if not user.company_id:
        return {"records": []}
    emp = await db.employees.find_one({"$or": [{"email": user.email}, {"user_id": user.user_id}], "company_id": user.company_id}, {"_id": 0})
    if not emp:
        return {"records": []}
    docs = await db.training_records.find(
        {"company_id": user.company_id, "employee_id": emp["employee_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=200)
    return {"records": docs}
