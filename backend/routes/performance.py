"""
Performance Management Routes
- Appraisals (annual/quarterly cycles)
- Objectives (SMART goals with progress)
- Review notes (manager 1-on-1s)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from pathlib import Path
import os, sys, uuid, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/performance", tags=["Performance"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


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


# ==================== APPRAISALS ====================

class AppraisalCreate(BaseModel):
    employee_id: str
    cycle: str = Field(..., description="e.g. '2025-Annual' or '2025-Q1'")
    period_start: str
    period_end: str
    reviewer_id: Optional[str] = None
    self_assessment: Optional[str] = None
    manager_assessment: Optional[str] = None
    overall_rating: Optional[str] = Field(None, description="exceeds | meets | partial | below")
    strengths: Optional[List[str]] = None
    development_areas: Optional[List[str]] = None
    salary_review_recommendation: Optional[str] = None


@router.post("/appraisals")
async def create_appraisal(data: AppraisalCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    now = datetime.now(timezone.utc)
    aid = f"appr_{uuid.uuid4().hex[:12]}"
    doc = {
        "review_id": aid,       # Supabase PK for appraisals table
        "appraisal_id": aid,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "cycle": data.cycle,
        "period_start": data.period_start,
        "period_end": data.period_end,
        "reviewer_id": data.reviewer_id or user.user_id,
        "self_assessment": data.self_assessment,
        "manager_assessment": data.manager_assessment,
        "overall_rating": data.overall_rating,
        "strengths": data.strengths or [],
        "development_areas": data.development_areas or [],
        "salary_review_recommendation": data.salary_review_recommendation,
        "status": "draft",
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.appraisals.insert_one(doc)
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "appraisal_created", "appraisal", aid,
                             {"employee_id": data.employee_id, "cycle": data.cycle})
    doc.pop("_id", None)
    return doc


@router.get("/appraisals")
async def list_appraisals(
    employee_id: Optional[str] = None,
    cycle: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user)
):
    if not user.company_id:
        return {"appraisals": [], "total": 0}
    query = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    if cycle:
        query["cycle"] = cycle
    rows = await db.appraisals.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"appraisals": rows, "total": len(rows)}


@router.put("/appraisals/{appraisal_id}")
async def update_appraisal(appraisal_id: str, data: dict, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    allowed = ["self_assessment", "manager_assessment", "overall_rating", "strengths",
               "development_areas", "salary_review_recommendation", "status",
               "employee_acknowledged_at", "manager_signed_at"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    # appraisals table PK is review_id; try both for compatibility
    filt = {"company_id": user.company_id}
    existing = await db.appraisals.find_one({"review_id": appraisal_id, "company_id": user.company_id}, {"_id": 0})
    if existing:
        filt["review_id"] = appraisal_id
    else:
        existing = await db.appraisals.find_one({"appraisal_id": appraisal_id, "company_id": user.company_id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="Appraisal not found")
        filt["appraisal_id"] = appraisal_id
    result = await db.appraisals.update_one(filt, {"$set": update})
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "appraisal_updated",
                             "appraisal", appraisal_id, update)
    return {"message": "Appraisal updated"}


# ==================== OBJECTIVES (SMART goals) ====================

class ObjectiveCreate(BaseModel):
    employee_id: str
    title: str
    description: Optional[str] = None
    target_date: Optional[str] = None
    measure: Optional[str] = None
    weight: int = Field(100, ge=1, le=100, description="% weight in appraisal")


@router.post("/objectives")
async def create_objective(data: ObjectiveCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    now = datetime.now(timezone.utc)
    oid = f"obj_{uuid.uuid4().hex[:12]}"
    doc = {
        "record_id": oid,       # Supabase PK for objectives table
        "objective_id": oid,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "title": data.title,
        "description": data.description,
        "target_date": data.target_date,
        "due_date": data.target_date,   # schema column alias
        "measure": data.measure,
        "weight": data.weight,
        "progress": 0,
        "status": "active",
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.objectives.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/objectives")
async def list_objectives(
    employee_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user)
):
    if not user.company_id:
        return {"objectives": [], "total": 0}
    query = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    rows = await db.objectives.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"objectives": rows, "total": len(rows)}


@router.put("/objectives/{objective_id}")
async def update_objective(objective_id: str, data: dict, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    allowed = ["title", "description", "target_date", "measure", "weight", "progress", "status"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    filt = {"company_id": user.company_id}
    ex = await db.objectives.find_one({"record_id": objective_id, "company_id": user.company_id}, {"_id": 0})
    filt["record_id" if ex else "objective_id"] = objective_id
    result = await db.objectives.update_one(filt, {"$set": update})
    return {"message": "Objective updated"}


@router.delete("/objectives/{objective_id}")
async def delete_objective(objective_id: str, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    filt = {"company_id": user.company_id}
    ex = await db.objectives.find_one({"record_id": objective_id, "company_id": user.company_id}, {"_id": 0})
    filt["record_id" if ex else "objective_id"] = objective_id
    result = await db.objectives.delete_one(filt)
    return {"message": "Deleted"}


# ==================== REVIEW NOTES (1-on-1s) ====================

class ReviewNoteCreate(BaseModel):
    employee_id: str
    note_type: str = Field(..., description="one_on_one | feedback | praise | concern")
    title: str
    content: str
    private: bool = False  # If true, only manager + HR can see


@router.post("/notes")
async def create_review_note(data: ReviewNoteCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    now = datetime.now(timezone.utc)
    nid = f"note_{uuid.uuid4().hex[:12]}"
    doc = {
        "record_id": nid,       # Supabase PK for review_notes table
        "note_id": nid,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "author_id": user.user_id,
        "author_name": user.name,
        "note_type": data.note_type,
        "type": data.note_type,         # schema column alias
        "title": data.title,
        "content": data.content,
        "note": data.content,           # schema column alias
        "private": data.private,
        "created_at": now.isoformat(),
    }
    await db.review_notes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/notes")
async def list_review_notes(
    employee_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user)
):
    if not user.company_id:
        return {"notes": [], "total": 0}
    query = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    # Filter out private notes if user is not the employee themselves or hr/admin/owner
    rows = await db.review_notes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    if user.role not in ("owner", "admin", "hr_manager", "manager"):
        rows = [r for r in rows if not r.get("private")]
    return {"notes": rows, "total": len(rows)}
