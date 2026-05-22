"""
RealtouchHR - GDPR / Data Protection Centre Routes
- Self-service data export (Article 15)
- Right to erasure / "right to be forgotten" (Article 17)
- HR/Admin overview of personal data held
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import os, sys, json, io, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

from services.gdpr_service import (
    build_user_export,
    create_erasure_request,
    list_erasure_requests,
    process_erasure_request,
    list_company_personal_data_overview,
)

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None
    employee_id: Optional[str] = None
    is_platform_admin: bool = False

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


def _require_hr(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="HR/Admin only")


# ==================== SELF-SERVICE EXPORT ====================

@router.get("/my-data")
async def my_data_export(user: CurrentUser = Depends(get_current_user)):
    """
    UK GDPR Article 15 — Subject Access Request (instant self-service).
    Returns a JSON bundle of all personal data held about the requesting user.
    """
    bundle = await build_user_export(
        user_id=user.user_id,
        email=user.email,
        company_id=user.company_id,
        employee_id=getattr(user, "employee_id", None),
    )
    return bundle


@router.get("/my-data/download")
async def my_data_download(user: CurrentUser = Depends(get_current_user)):
    """Download the same bundle as a .json file."""
    bundle = await build_user_export(
        user_id=user.user_id,
        email=user.email,
        company_id=user.company_id,
        employee_id=getattr(user, "employee_id", None),
    )
    body = json.dumps(bundle, indent=2, default=str).encode("utf-8")
    filename = f"realtouchhr_data_export_{user.user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    return StreamingResponse(
        io.BytesIO(body),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ==================== RIGHT TO ERASURE ====================

class ErasureRequestBody(BaseModel):
    reason: Optional[str] = None


@router.post("/erasure")
async def submit_erasure(data: ErasureRequestBody, user: CurrentUser = Depends(get_current_user)):
    """Employee/user submits a 'right to be forgotten' request. HR/Admin must approve."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company context")
    # Prevent platform admin from erasing themselves (would lock the platform)
    if getattr(user, "is_platform_admin", False):
        raise HTTPException(status_code=400, detail="Platform admins cannot submit erasure requests via this endpoint")
    # Block duplicates
    existing = await db.gdpr_erasure_requests.find_one(
        {"user_id": user.user_id, "status": "pending"}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending erasure request")
    req = await create_erasure_request(
        user_id=user.user_id,
        company_id=user.company_id,
        requester_email=user.email,
        reason=data.reason,
    )
    return req


@router.get("/erasure")
async def list_erasure(status: Optional[str] = None, user: CurrentUser = Depends(get_current_user)):
    """HR/Admin lists erasure requests for the company."""
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    return await list_erasure_requests(user.company_id, status=status)


class ProcessErasureBody(BaseModel):
    action: str  # approve_anonymize | approve_delete | reject
    notes: Optional[str] = None


@router.post("/erasure/{request_id}/process")
async def process_erasure(request_id: str, body: ProcessErasureBody, user: CurrentUser = Depends(get_current_user)):
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    if body.action not in ("approve_anonymize", "approve_delete", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action")
    result = await process_erasure_request(
        request_id=request_id,
        company_id=user.company_id,
        processor_user_id=user.user_id,
        processor_name=user.name,
        action=body.action,
        notes=body.notes,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Process failed"))
    return result


# ==================== COMPANY-LEVEL OVERVIEW (HR/Admin) ====================

@router.get("/overview")
async def company_overview(user: CurrentUser = Depends(get_current_user)):
    """HR/Admin: how much personal data we hold for this company + retention policy."""
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    return await list_company_personal_data_overview(user.company_id)
