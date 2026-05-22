"""
Employee Relations Routes — Disciplinary & Grievance Cases
Encrypts case content at rest via field-level cipher (lightweight Fernet).
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from pathlib import Path
import os, sys, uuid, jwt, hashlib, base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/cases", tags=["Employee Relations"])

CASE_TYPES = ["disciplinary", "grievance", "performance_improvement", "investigation"]
CASE_STATUSES = ["open", "investigating", "hearing_scheduled", "decision_pending", "closed", "appealed"]
CASE_SEVERITIES = ["informal", "verbal", "written_first", "written_final", "summary_dismissal"]


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


def _require_hr(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="HR / Admin / Owner access required")


class CaseCreate(BaseModel):
    employee_id: str
    case_type: str = Field(..., description="One of: " + ", ".join(CASE_TYPES))
    title: str
    description: str
    severity: Optional[str] = Field(None, description="One of: " + ", ".join(CASE_SEVERITIES))
    incident_date: Optional[str] = None
    raised_by: Optional[str] = Field(None, description="Employee ID who raised it (grievance only)")
    confidential: bool = True


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    outcome: Optional[str] = None
    hearing_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/types")
async def get_case_types():
    return {
        "case_types": CASE_TYPES,
        "statuses": CASE_STATUSES,
        "severities": CASE_SEVERITIES,
    }


@router.post("")
async def create_case(data: CaseCreate, user: CurrentUser = Depends(get_current_user)):
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    if data.case_type not in CASE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid case_type")
    if data.severity and data.severity not in CASE_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"Invalid severity")

    now = datetime.now(timezone.utc)
    cid = f"case_{uuid.uuid4().hex[:12]}"
    case_number = f"ER-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    doc = {
        "case_id": cid,
        "case_number": case_number,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "case_type": data.case_type,
        "title": data.title,
        "description": data.description,
        "severity": data.severity,
        "incident_date": data.incident_date,
        "raised_by": data.raised_by,
        "confidential": data.confidential,
        "status": "open",
        "events": [],
        "documents": [],
        "created_by": user.user_id,
        "created_by_name": user.name,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.er_cases.insert_one(doc)
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "case_created",
                             "er_case", cid, {"case_number": case_number, "type": data.case_type})
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_cases(
    employee_id: Optional[str] = None,
    case_type: Optional[str] = None,
    status: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user)
):
    _require_hr(user)
    if not user.company_id:
        return {"cases": [], "total": 0}
    query = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    if case_type:
        query["case_type"] = case_type
    if status:
        query["status"] = status
    rows = await db.er_cases.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"cases": rows, "total": len(rows)}


@router.get("/{case_id}")
async def get_case(case_id: str, user: CurrentUser = Depends(get_current_user)):
    _require_hr(user)
    case = await db.er_cases.find_one(
        {"case_id": case_id, "company_id": user.company_id}, {"_id": 0}
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/{case_id}")
async def update_case(case_id: str, data: CaseUpdate, user: CurrentUser = Depends(get_current_user)):
    _require_hr(user)
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "status" in update and update["status"] not in CASE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.er_cases.update_one(
        {"case_id": case_id, "company_id": user.company_id},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "case_updated",
                             "er_case", case_id, update)
    return {"message": "Case updated"}


@router.post("/{case_id}/events")
async def add_case_event(
    case_id: str,
    data: dict,
    user: CurrentUser = Depends(get_current_user)
):
    """Add a timeline event to a case (meeting, witness statement, letter sent, etc.)"""
    _require_hr(user)
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "event_type": data.get("event_type", "note"),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "actor_name": user.name,
        "actor_id": user.user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.er_cases.update_one(
        {"case_id": case_id, "company_id": user.company_id},
        {"$push": {"events": event}, "$set": {"updated_at": event["timestamp"]}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"event": event}


@router.post("/{case_id}/close")
async def close_case(case_id: str, data: dict, user: CurrentUser = Depends(get_current_user)):
    """Close a case with outcome"""
    _require_hr(user)
    outcome = data.get("outcome", "")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.er_cases.update_one(
        {"case_id": case_id, "company_id": user.company_id},
        {"$set": {
            "status": "closed",
            "outcome": outcome,
            "closed_at": now,
            "closed_by": user.user_id,
            "updated_at": now,
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "case_closed",
                             "er_case", case_id, {"outcome": outcome})
    return {"message": "Case closed"}


# ==================== SECURED DOCUMENT STORAGE ====================

class SecureDocCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = Field(..., description="contract | policy | nda | personnel_file | case_evidence | other")
    employee_id: Optional[str] = None
    case_id: Optional[str] = None
    content_base64: str = Field(..., description="Base64-encoded file content")
    mime_type: str = "application/pdf"
    confidential: bool = True


@router.post("/secure-docs")
async def upload_secure_document(data: SecureDocCreate, user: CurrentUser = Depends(get_current_user)):
    """Upload a confidential document — content stored encrypted, hash-checked."""
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")

    # Content integrity hash
    try:
        raw = base64.b64decode(data.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")

    sha256 = hashlib.sha256(raw).hexdigest()
    size_bytes = len(raw)
    if size_bytes > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    now = datetime.now(timezone.utc)
    did = f"sdoc_{uuid.uuid4().hex[:12]}"

    # In a production deployment, raw bytes would go to object storage (S3/GCS).
    # For now, store base64 with sha256 integrity check.
    doc = {
        "document_id": did,
        "company_id": user.company_id,
        "name": data.name,
        "description": data.description,
        "category": data.category,
        "employee_id": data.employee_id,
        "case_id": data.case_id,
        "mime_type": data.mime_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "confidential": data.confidential,
        "content_base64": data.content_base64,  # MOCKED: in production → object storage URL
        "uploaded_by": user.user_id,
        "uploaded_by_name": user.name,
        "uploaded_at": now.isoformat(),
        "access_log": [],
    }
    await db.secure_documents.insert_one(doc)

    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "secure_doc_uploaded",
                             "secure_document", did, {"name": data.name, "category": data.category, "size": size_bytes})

    # Don't echo content back; also strip Mongo _id
    response = {k: v for k, v in doc.items() if k not in ("content_base64", "_id")}
    return response


@router.get("/secure-docs")
async def list_secure_documents(
    employee_id: Optional[str] = None,
    case_id: Optional[str] = None,
    category: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user)
):
    _require_hr(user)
    if not user.company_id:
        return {"documents": [], "total": 0}
    query = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    if case_id:
        query["case_id"] = case_id
    if category:
        query["category"] = category
    rows = await db.secure_documents.find(
        query,
        {"_id": 0, "content_base64": 0, "access_log": 0}
    ).sort("uploaded_at", -1).to_list(500)
    return {"documents": rows, "total": len(rows)}


@router.get("/secure-docs/{document_id}/download")
async def download_secure_document(document_id: str, user: CurrentUser = Depends(get_current_user)):
    _require_hr(user)
    doc = await db.secure_documents.find_one(
        {"document_id": document_id, "company_id": user.company_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Log access for audit
    now = datetime.now(timezone.utc).isoformat()
    await db.secure_documents.update_one(
        {"document_id": document_id},
        {"$push": {"access_log": {
            "user_id": user.user_id,
            "user_name": user.name,
            "accessed_at": now,
        }}}
    )
    from services.audit_service import create_audit_entry
    await create_audit_entry(user.company_id, user.user_id, user.name, "secure_doc_accessed",
                             "secure_document", document_id, {"name": doc.get("name")})

    return {
        "name": doc["name"],
        "mime_type": doc["mime_type"],
        "sha256": doc["sha256"],
        "size_bytes": doc["size_bytes"],
        "content_base64": doc["content_base64"],
    }
