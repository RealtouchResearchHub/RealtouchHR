"""
RealtouchHR - Right to Work (RTW) Routes
UK Right to Work Check Management API

API endpoints for recording and managing RTW checks.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rtw", tags=["Right to Work"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class RecordRTWCheckRequest(BaseModel):
    employee_id: str
    check_date: str  # ISO format YYYY-MM-DD
    check_type: str  # manual, idvt, home_office_online, share_code
    document_type: str
    document_number: Optional[str] = None
    document_expiry_date: Optional[str] = None  # ISO format YYYY-MM-DD, null if permanent
    share_code: Optional[str] = None
    online_check_reference: Optional[str] = None
    document_copy_url: Optional[str] = None
    notes: Optional[str] = None
    confirmation_signed: bool = Field(
        ...,
        description="Confirm original document was seen and appears genuine"
    )


class UpdateRTWCheckRequest(BaseModel):
    document_number: Optional[str] = None
    document_expiry_date: Optional[str] = None
    notes: Optional[str] = None


# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> User:
    """Get current authenticated user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=401, detail="User not found")
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def require_hr_admin(request: Request) -> User:
    """Require HR admin or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "hr_admin"]:
        raise HTTPException(
            status_code=403,
            detail="HR Admin access required"
        )
    return user


# ==================== RTW CHECK ROUTES ====================

@router.post("/check")
async def record_rtw_check(
    request_data: RecordRTWCheckRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Record a new Right to Work check.
    
    This creates an immutable record of the RTW check performed.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not request_data.confirmation_signed:
        raise HTTPException(
            status_code=400,
            detail="You must confirm you have seen the original document"
        )
    
    # Parse dates
    check_date = date.fromisoformat(request_data.check_date)
    document_expiry = None
    if request_data.document_expiry_date:
        document_expiry = date.fromisoformat(request_data.document_expiry_date)
    
    from services.rtw_service import rtw_service
    
    try:
        check = await rtw_service.record_rtw_check(
            employee_id=request_data.employee_id,
            company_id=user.company_id,
            check_date=check_date,
            check_type=request_data.check_type,
            document_type=request_data.document_type,
            conducted_by=user.user_id,
            document_number=request_data.document_number,
            document_expiry_date=document_expiry,
            share_code=request_data.share_code,
            online_check_reference=request_data.online_check_reference,
            document_copy_url=request_data.document_copy_url,
            notes=request_data.notes,
            confirmation_signed=request_data.confirmation_signed
        )
        return check.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employees/{employee_id}")
async def get_employee_rtw_checks(
    employee_id: str,
    user: User = Depends(require_hr_admin)
):
    """
    Get all RTW checks for an employee.
    
    Returns check history in reverse chronological order.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rtw_service import rtw_service
    
    checks = await rtw_service.get_employee_rtw_checks(employee_id, user.company_id)
    
    return {"checks": checks, "total": len(checks)}


@router.get("/employees/{employee_id}/status")
async def get_employee_rtw_status(
    employee_id: str,
    user: User = Depends(require_hr_admin)
):
    """
    Get current RTW status for an employee.
    
    Shows status, expiry date, and latest check information.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rtw_service import rtw_service
    
    try:
        status = await rtw_service.get_employee_rtw_status(employee_id, user.company_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary")
async def get_rtw_summary(user: User = Depends(require_hr_admin)):
    """
    Get RTW status summary across all employees.
    
    Returns counts by status: valid, permanent, expiring_soon, expired, not_checked.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rtw_service import rtw_service
    
    summary = await rtw_service.get_rtw_summary(user.company_id)
    return summary


@router.get("/expiring")
async def get_expiring_rtw(
    days: int = 60,
    user: User = Depends(require_hr_admin)
):
    """
    Get employees with RTW expiring within N days.
    
    Default is 60 days, but can be customized.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rtw_service import rtw_service
    
    employees = await rtw_service.get_expiring_rtw(user.company_id, days)
    
    return {"employees": employees, "total": len(employees), "days": days}


@router.post("/bulk-check")
async def bulk_status_update(user: User = Depends(require_hr_admin)):
    """
    Trigger re-evaluation of RTW status for all employees.
    
    Run this after importing employees or to refresh statuses.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rtw_service import rtw_service
    
    result = await rtw_service.bulk_status_update(user.company_id)
    return result


@router.get("/check-types")
async def get_check_types(user: User = Depends(get_current_user)):
    """
    Get available RTW check types.
    """
    from services.rtw_service import RTWCheckType
    
    return {
        "check_types": [
            {"code": RTWCheckType.MANUAL.value, "name": "Manual Document Check"},
            {"code": RTWCheckType.IDVT.value, "name": "IDVT via Certified Provider"},
            {"code": RTWCheckType.HOME_OFFICE_ONLINE.value, "name": "Home Office Online Check"},
            {"code": RTWCheckType.SHARE_CODE.value, "name": "Share Code Check"}
        ]
    }


@router.get("/document-types/{check_type}")
async def get_document_types(
    check_type: str,
    user: User = Depends(get_current_user)
):
    """
    Get valid document types for a check type.
    """
    from services.rtw_service import rtw_service
    
    doc_types = rtw_service.get_document_types_for_check_type(check_type)
    
    return {"document_types": doc_types}


@router.put("/check/{check_id}")
async def update_rtw_check(
    check_id: str,
    request_data: UpdateRTWCheckRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Update a RTW check record.
    
    Only certain fields can be updated (corrections).
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Verify check exists and belongs to company
    check = await db.rtw_checks.find_one(
        {"check_id": check_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not check:
        raise HTTPException(status_code=404, detail="RTW check not found")
    
    updates = request_data.dict(exclude_unset=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = user.user_id
    
    await db.rtw_checks.update_one(
        {"check_id": check_id},
        {"$set": updates}
    )
    
    # Update employee status
    from services.rtw_service import rtw_service
    await rtw_service._update_employee_rtw_status(check["employee_id"])
    
    return {"status": "updated", "check_id": check_id}
