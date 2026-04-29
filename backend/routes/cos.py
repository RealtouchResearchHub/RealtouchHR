"""
RealtouchHR - Certificate of Sponsorship (CoS) Routes
CoS Register Management API

API endpoints for managing Certificates of Sponsorship.
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

router = APIRouter(prefix="/cos", tags=["Certificate of Sponsorship"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class CreateCoSRequest(BaseModel):
    cos_reference_number: str = Field(..., min_length=1, max_length=50)
    cos_type: str  # defined or undefined
    job_title: str
    soc_code: str
    salary_offered: float = Field(..., gt=0)
    hours_per_week: float = Field(default=37.5, ge=1, le=168)
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None  # ISO format
    employee_id: Optional[str] = None
    notes: Optional[str] = None


class UpdateCoSRequest(BaseModel):
    job_title: Optional[str] = None
    salary_offered: Optional[float] = None
    hours_per_week: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class AssignCoSRequest(BaseModel):
    employee_id: str


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


# ==================== COS ROUTES ====================

@router.post("")
async def create_cos(
    request_data: CreateCoSRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Create a new Certificate of Sponsorship record.
    
    CoS reference numbers are obtained from the UKVI Sponsor Management System.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Parse dates
    start_date = date.fromisoformat(request_data.start_date) if request_data.start_date else None
    end_date = date.fromisoformat(request_data.end_date) if request_data.end_date else None
    
    from services.cos_service import cos_service
    
    try:
        cos = await cos_service.create_cos(
            company_id=user.company_id,
            cos_reference_number=request_data.cos_reference_number,
            cos_type=request_data.cos_type,
            job_title=request_data.job_title,
            soc_code=request_data.soc_code,
            salary_offered=request_data.salary_offered,
            hours_per_week=request_data.hours_per_week,
            start_date=start_date,
            end_date=end_date,
            employee_id=request_data.employee_id,
            notes=request_data.notes,
            created_by=user.user_id
        )
        return cos.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_cos(
    status: Optional[str] = None,
    user: User = Depends(require_hr_admin)
):
    """
    List all Certificates of Sponsorship.
    
    Filter by status: unassigned, assigned, used, expired, withdrawn, cancelled
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    records = await cos_service.get_all_cos(user.company_id, status)
    
    return {"certificates": records, "total": len(records)}


@router.get("/expiring")
async def get_expiring_cos(
    days: int = 60,
    user: User = Depends(require_hr_admin)
):
    """
    Get CoS expiring within N days.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    records = await cos_service.get_expiring_cos(user.company_id, days)
    
    return {"certificates": records, "total": len(records), "days": days}


@router.get("/salary-checks")
async def check_salary_thresholds(user: User = Depends(require_hr_admin)):
    """
    Check all sponsored workers against salary thresholds.
    
    Returns employees whose salary is below the general threshold or going rate.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    issues = await cos_service.check_salary_thresholds(user.company_id)
    
    return {
        "issues": issues,
        "total_issues": len(issues),
        "general_threshold": cos_service.general_threshold,
        "new_entrant_threshold": cos_service.new_entrant_threshold
    }


@router.get("/{cos_id}")
async def get_cos(
    cos_id: str,
    user: User = Depends(require_hr_admin)
):
    """
    Get a single CoS record.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    try:
        cos = await cos_service.get_cos(cos_id, user.company_id)
        return cos
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{cos_id}")
async def update_cos(
    cos_id: str,
    request_data: UpdateCoSRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Update a CoS record.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    updates = request_data.dict(exclude_unset=True)
    
    # Parse dates if present
    if "start_date" in updates and updates["start_date"]:
        updates["start_date"] = updates["start_date"]
    if "end_date" in updates and updates["end_date"]:
        updates["end_date"] = updates["end_date"]
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.certificates_of_sponsorship.update_one(
        {"cos_id": cos_id, "company_id": user.company_id},
        {"$set": updates}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="CoS not found")
    
    return {"status": "updated", "cos_id": cos_id}


@router.post("/{cos_id}/assign")
async def assign_cos(
    cos_id: str,
    request_data: AssignCoSRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Assign a CoS to an employee.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    try:
        result = await cos_service.assign_cos(
            cos_id=cos_id,
            employee_id=request_data.employee_id,
            company_id=user.company_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{cos_id}")
async def delete_cos(
    cos_id: str,
    user: User = Depends(require_hr_admin)
):
    """
    Cancel (soft delete) a CoS.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.cos_service import cos_service
    
    try:
        result = await cos_service.delete_cos(cos_id, user.company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== SOC CODE ROUTES ====================

@router.get("/soc-codes/search")
async def search_soc_codes(
    query: str,
    user: User = Depends(get_current_user)
):
    """
    Search SOC codes by code or job title.
    """
    from services.cos_service import cos_service
    
    results = cos_service.search_soc_codes(query)
    
    return {"soc_codes": results, "total": len(results)}


@router.get("/soc-codes/{soc_code}/going-rate")
async def get_soc_going_rate(
    soc_code: str,
    user: User = Depends(get_current_user)
):
    """
    Get the going rate for a SOC code.
    """
    from services.cos_service import cos_service
    
    rate = cos_service.get_soc_going_rate(soc_code)
    
    if "error" in rate:
        raise HTTPException(status_code=404, detail=rate["error"])
    
    return rate
