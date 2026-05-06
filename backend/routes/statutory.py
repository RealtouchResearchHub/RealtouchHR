"""
RealtouchHR - Statutory Payments Routes
SSP / SMP / SPP calculations and records
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import os, sys, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import jwt

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statutory", tags=["Statutory Payments"])


# ==================== MODELS ====================

class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class SSPCalcRequest(BaseModel):
    employee_id: str
    sick_start_date: str
    sick_end_date: str
    qualifying_days_per_week: int = Field(5, ge=1, le=7)


class SMPCalcRequest(BaseModel):
    employee_id: str
    expected_week_of_childbirth: str
    maternity_start_date: str
    is_small_employer: bool = False


class SPPCalcRequest(BaseModel):
    employee_id: str
    birth_date: str
    paternity_weeks: int = Field(2, ge=1, le=2)


class RecordRequest(BaseModel):
    employee_id: str
    payment_type: str  # ssp, smp, spp, shpp, sap
    start_date: str
    end_date: Optional[str] = None
    calculation: Dict[str, Any]
    notes: Optional[str] = None


# ==================== AUTH ====================

async def get_current_user(request: Request) -> CurrentUser:
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            session_token = auth.split(" ")[1]
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})

    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


# ==================== ROUTES ====================

@router.post("/ssp/calculate")
async def calc_ssp(req: SSPCalcRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    try:
        result = await statutory_service.calculate_ssp(
            employee_id=req.employee_id,
            company_id=user.company_id,
            sick_start_date=date.fromisoformat(req.sick_start_date),
            sick_end_date=date.fromisoformat(req.sick_end_date),
            qualifying_days_per_week=req.qualifying_days_per_week
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/smp/calculate")
async def calc_smp(req: SMPCalcRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    try:
        result = await statutory_service.calculate_smp(
            employee_id=req.employee_id,
            company_id=user.company_id,
            expected_week_of_childbirth=date.fromisoformat(req.expected_week_of_childbirth),
            maternity_start_date=date.fromisoformat(req.maternity_start_date),
            is_small_employer=req.is_small_employer
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/spp/calculate")
async def calc_spp(req: SPPCalcRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    try:
        result = await statutory_service.calculate_spp(
            employee_id=req.employee_id,
            company_id=user.company_id,
            birth_date=date.fromisoformat(req.birth_date),
            paternity_weeks=req.paternity_weeks
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/record")
async def record_statutory_payment(req: RecordRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    try:
        payment = await statutory_service.create_statutory_payment(
            employee_id=req.employee_id,
            company_id=user.company_id,
            payment_type=req.payment_type,
            start_date=date.fromisoformat(req.start_date),
            end_date=date.fromisoformat(req.end_date) if req.end_date else None,
            calculation=req.calculation,
            created_by=user.user_id,
            notes=req.notes
        )
        return {"payment": payment.to_dict(), "message": "Statutory payment recorded"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employee/{employee_id}")
async def get_employee_statutory(employee_id: str, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    payments = await statutory_service.get_employee_statutory_payments(employee_id, user.company_id)
    return {"payments": payments, "total": len(payments)}


@router.get("/active")
async def get_active_statutory(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    payments = await statutory_service.get_active_statutory_payments(user.company_id)
    return {"payments": payments, "total": len(payments)}


@router.get("/eps-summary")
async def get_eps_summary(
    tax_month: int = 1,
    tax_year: str = "2025-26",
    user: CurrentUser = Depends(get_current_user)
):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.statutory_service import statutory_service
    return await statutory_service.get_eps_recovery_summary(user.company_id, tax_month, tax_year)


@router.get("/rates")
async def get_statutory_rates():
    """Return 2025-26 statutory rates (for UI display)"""
    from services.statutory_service import (
        SSP_WEEKLY_RATE, SMP_STANDARD_WEEKLY_RATE, SPP_WEEKLY_RATE,
        SHPP_WEEKLY_RATE, SAP_STANDARD_WEEKLY_RATE, LOWER_EARNINGS_LIMIT,
        SMALL_EMPLOYER_RECOVERY_RATE, STANDARD_RECOVERY_RATE
    )
    return {
        "tax_year": "2025-26",
        "ssp_weekly_rate": SSP_WEEKLY_RATE,
        "smp_weekly_rate": SMP_STANDARD_WEEKLY_RATE,
        "spp_weekly_rate": SPP_WEEKLY_RATE,
        "shpp_weekly_rate": SHPP_WEEKLY_RATE,
        "sap_weekly_rate": SAP_STANDARD_WEEKLY_RATE,
        "lower_earnings_limit": LOWER_EARNINGS_LIMIT,
        "small_employer_recovery_rate": SMALL_EMPLOYER_RECOVERY_RATE,
        "standard_recovery_rate": STANDARD_RECOVERY_RATE
    }
