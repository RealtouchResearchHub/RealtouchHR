"""
RealtouchHR - Offboarding Routes
Employee termination workflow endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import os, sys, logging
from pathlib import Path
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/offboarding", tags=["Offboarding"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class TerminateRequest(BaseModel):
    employee_id: str
    leaving_date: str
    reason: str
    notes: Optional[str] = None
    redundancy_payment: float = 0.0
    holiday_payout_days: float = 0.0


async def get_current_user(request: Request) -> CurrentUser:
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            session_token = auth.split(" ")[1]
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if session:
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    else:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


@router.get("/reasons")
async def get_termination_reasons():
    from services.offboarding_service import TERMINATION_REASONS
    return {"reasons": TERMINATION_REASONS}


@router.post("/terminate")
async def terminate_employee(req: TerminateRequest, user: CurrentUser = Depends(get_current_user)):
    if user.role not in ("owner", "admin", "hr_admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="You do not have permission to terminate employees")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.offboarding_service import offboarding_service
    try:
        result = await offboarding_service.terminate_employee(
            employee_id=req.employee_id,
            company_id=user.company_id,
            leaving_date=req.leaving_date,
            reason=req.reason,
            notes=req.notes,
            redundancy_payment=req.redundancy_payment,
            holiday_payout_days=req.holiday_payout_days,
            user_id=user.user_id,
            user_name=user.name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Termination failed: {e}")
        raise HTTPException(status_code=500, detail=f"Termination failed: {e}")


@router.get("/list")
async def list_terminations(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    from services.offboarding_service import offboarding_service
    terminations = await offboarding_service.list_terminations(user.company_id)
    return {"terminations": terminations, "total": len(terminations)}


@router.post("/reinstate/{employee_id}")
async def reinstate_employee(employee_id: str, user: CurrentUser = Depends(get_current_user)):
    """Undo termination (clear leaver status)"""
    if user.role not in ("owner", "admin", "hr_admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="You do not have permission to reinstate employees")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    now = datetime.now(timezone.utc).isoformat()
    result = await db.employees.update_one(
        {"employee_id": employee_id, "company_id": user.company_id, "status": "terminated"},
        {"$set": {
            "status": "active",
            "updated_at": now,
        }, "$unset": {
            "leaving_date": "",
            "terminated_at": "",
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Terminated employee not found")
    # Remove from leaver queue
    await db.rti_leaver_queue.delete_many({"employee_id": employee_id, "company_id": user.company_id, "status": "queued"})
    return {"message": "Employee reinstated", "employee_id": employee_id}
