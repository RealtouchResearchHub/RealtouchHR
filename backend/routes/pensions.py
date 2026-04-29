"""
RealtouchHR - Pension Auto-Enrolment Routes
UK Workplace Pension Compliance API

API endpoints for pension scheme management and auto-enrolment.
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

router = APIRouter(prefix="/pensions", tags=["Pensions"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class CreateSchemeRequest(BaseModel):
    scheme_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=100)
    employer_reference: str
    pension_type: str = "defined_contribution"
    employer_contribution_pct: float = Field(..., ge=3.0)  # Min 3%
    employee_contribution_pct: float = Field(..., ge=0)
    qualifying_basis: str = "qualifying_earnings"
    is_default: bool = False
    staging_date: Optional[str] = None


class UpdateSchemeRequest(BaseModel):
    scheme_name: Optional[str] = None
    provider: Optional[str] = None
    employer_contribution_pct: Optional[float] = None
    employee_contribution_pct: Optional[float] = None
    is_default: Optional[bool] = None


class EnrolEmployeeRequest(BaseModel):
    employee_id: str
    scheme_id: Optional[str] = None
    employee_contribution_override: Optional[float] = None
    employer_contribution_override: Optional[float] = None


class OptOutRequest(BaseModel):
    opt_out_reference: str = Field(..., min_length=1)


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


async def require_payroll_admin(request: Request) -> User:
    """Require payroll admin or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "payroll_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Payroll Admin access required"
        )
    return user


# ==================== SCHEME ROUTES ====================

@router.post("/schemes")
async def create_pension_scheme(
    request_data: CreateSchemeRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Create a new pension scheme.
    
    Minimum employer contribution is 3%, total must be at least 8%.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    staging_date = None
    if request_data.staging_date:
        staging_date = date.fromisoformat(request_data.staging_date)
    
    from services.pension_service import pension_service
    
    try:
        scheme = await pension_service.create_scheme(
            company_id=user.company_id,
            scheme_name=request_data.scheme_name,
            provider=request_data.provider,
            employer_reference=request_data.employer_reference,
            pension_type=request_data.pension_type,
            employer_contribution_pct=request_data.employer_contribution_pct,
            employee_contribution_pct=request_data.employee_contribution_pct,
            qualifying_basis=request_data.qualifying_basis,
            is_default=request_data.is_default,
            staging_date=staging_date
        )
        return scheme.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schemes")
async def list_pension_schemes(user: User = Depends(get_current_user)):
    """
    List all pension schemes for the company.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    schemes = await pension_service.get_schemes(user.company_id)
    
    return {"schemes": schemes, "total": len(schemes)}


@router.put("/schemes/{scheme_id}")
async def update_pension_scheme(
    scheme_id: str,
    request_data: UpdateSchemeRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Update a pension scheme.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    updates = request_data.dict(exclude_unset=True)
    
    try:
        result = await pension_service.update_scheme(scheme_id, user.company_id, updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== ASSESSMENT ROUTES ====================

@router.get("/assess/{employee_id}")
async def assess_employee_enrolment(
    employee_id: str,
    annual_earnings: float,
    user: User = Depends(require_payroll_admin)
):
    """
    Assess an employee for auto-enrolment.
    
    Returns worker category and recommended action.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    try:
        assessment = await pension_service.assess_employee_enrolment(
            employee_id,
            user.company_id,
            annual_earnings
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/assess")
async def run_bulk_assessment(
    pay_run_id: Optional[str] = None,
    user: User = Depends(require_payroll_admin)
):
    """
    Run auto-enrolment assessment for all employees.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    results = await pension_service.run_bulk_assessment(user.company_id, pay_run_id)
    
    return results


# ==================== ENROLMENT ROUTES ====================

@router.post("/enrolment")
async def enrol_employee(
    request_data: EnrolEmployeeRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Enrol an employee in a pension scheme.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    try:
        enrolment = await pension_service.enrol_employee(
            employee_id=request_data.employee_id,
            company_id=user.company_id,
            scheme_id=request_data.scheme_id,
            employee_contribution_override=request_data.employee_contribution_override,
            employer_contribution_override=request_data.employer_contribution_override
        )
        return enrolment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/enrolment")
async def list_enrolments(
    status: Optional[str] = None,
    user: User = Depends(require_payroll_admin)
):
    """
    List all pension enrolments.
    
    Filter by status: eligible, enrolled, opted_out, postponed, not_eligible
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    enrolments = await pension_service.get_enrolments(user.company_id, status)
    
    return {"enrolments": enrolments, "total": len(enrolments)}


@router.put("/enrolment/{employee_id}")
async def update_enrolment(
    employee_id: str,
    request_data: EnrolEmployeeRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Update an employee's pension enrolment.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    # Re-enrol with new settings
    try:
        enrolment = await pension_service.enrol_employee(
            employee_id=employee_id,
            company_id=user.company_id,
            scheme_id=request_data.scheme_id,
            employee_contribution_override=request_data.employee_contribution_override,
            employer_contribution_override=request_data.employer_contribution_override
        )
        return enrolment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/enrolment/{employee_id}/opt-out")
async def record_opt_out(
    employee_id: str,
    request_data: OptOutRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Record an employee opt-out from pension.
    
    Must be within 1 month of enrolment.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    try:
        result = await pension_service.record_opt_out(
            employee_id=employee_id,
            company_id=user.company_id,
            opt_out_reference=request_data.opt_out_reference
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== CONTRIBUTION ROUTES ====================

@router.get("/contribution-report/{pay_run_id}")
async def get_contribution_report(
    pay_run_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Get pension contribution report for a pay run.
    
    Lists employee and employer contributions for all enrolled employees.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.pension_service import pension_service
    
    try:
        report = await pension_service.get_contribution_report(
            user.company_id,
            pay_run_id
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/thresholds")
async def get_pension_thresholds(user: User = Depends(get_current_user)):
    """
    Get current auto-enrolment thresholds.
    """
    from services.pension_service import pension_service
    
    return {
        "lower_qualifying_earnings": pension_service.lower_threshold,
        "earnings_trigger": pension_service.trigger_threshold,
        "upper_qualifying_earnings": pension_service.upper_threshold,
        "state_pension_age": pension_service.state_pension_age,
        "min_employer_contribution_pct": 3.0,
        "min_total_contribution_pct": 8.0,
        "tax_year": "2025-26"
    }
