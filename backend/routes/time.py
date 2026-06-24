"""
RealtouchHR - Time & Scheduling Routes
Clock-in/out, Shifts, Rotas, and Timesheets API

Endpoints for employee time tracking, shift scheduling, and timesheet management.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/time", tags=["Time & Scheduling"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class ClockInRequest(BaseModel):
    employee_id: Optional[str] = None  # If not provided, uses logged-in user's employee record
    location: Optional[Dict[str, float]] = None  # {lat, lng}
    location_name: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    employee_id: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    location_name: Optional[str] = None
    notes: Optional[str] = None


class CreateShiftRequest(BaseModel):
    employee_id: str
    date: str  # ISO format YYYY-MM-DD
    start_time: str  # ISO datetime
    end_time: str  # ISO datetime
    break_duration_minutes: int = 30
    role: Optional[str] = None
    location: Optional[str] = None
    rota_id: Optional[str] = None
    notes: Optional[str] = None


class UpdateShiftRequest(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_duration_minutes: Optional[int] = None
    role: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CreateRotaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    week_start_date: str  # ISO format YYYY-MM-DD (must be a Monday)


class CopyRotaRequest(BaseModel):
    new_week_start_date: str  # ISO format YYYY-MM-DD


class TimesheetActionRequest(BaseModel):
    reason: Optional[str] = None  # For rejection


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


async def require_manager(request: Request) -> User:
    """Require manager, admin, or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "hr_admin", "manager"]:
        raise HTTPException(
            status_code=403,
            detail="Manager access required"
        )
    return user


# ==================== CLOCK ROUTES ====================

@router.post("/clock-in")
async def clock_in(
    request_data: ClockInRequest,
    user: User = Depends(get_current_user)
):
    """
    Record clock-in for an employee.
    
    If employee_id not provided, clocks in the current user.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Determine employee ID
    employee_id = request_data.employee_id
    if not employee_id:
        # Find employee record for current user
        employee = await db.employees.find_one(
            {"email": user.email, "company_id": user.company_id},
            {"employee_id": 1, "_id": 0}
        )
        if employee:
            employee_id = employee["employee_id"]
        else:
            raise HTTPException(status_code=400, detail="You need an employee record to clock in. Please contact your administrator.")

    from services.time_service import time_service
    
    try:
        event = await time_service.clock_in(
            employee_id=employee_id,
            company_id=user.company_id,
            location=request_data.location,
            location_name=request_data.location_name,
            device_info=request_data.device_info,
            notes=request_data.notes
        )
        return event.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clock-out")
async def clock_out(
    request_data: ClockOutRequest,
    user: User = Depends(get_current_user)
):
    """
    Record clock-out for an employee.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    employee_id = request_data.employee_id
    if not employee_id:
        employee = await db.employees.find_one(
            {"email": user.email, "company_id": user.company_id},
            {"employee_id": 1, "_id": 0}
        )
        if employee:
            employee_id = employee["employee_id"]
        else:
            raise HTTPException(status_code=404, detail="No employee record found for user")
    
    from services.time_service import time_service
    
    try:
        event = await time_service.clock_out(
            employee_id=employee_id,
            company_id=user.company_id,
            location=request_data.location,
            location_name=request_data.location_name,
            notes=request_data.notes
        )
        return event.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/break/start")
async def start_break(user: User = Depends(get_current_user)):
    """Start a break"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    employee = await db.employees.find_one(
        {"email": user.email, "company_id": user.company_id},
        {"employee_id": 1, "_id": 0}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="No employee record found")
    
    from services.time_service import time_service
    
    event = await time_service.start_break(
        employee_id=employee["employee_id"],
        company_id=user.company_id
    )
    return event.to_dict()


@router.post("/break/end")
async def end_break(user: User = Depends(get_current_user)):
    """End a break"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    employee = await db.employees.find_one(
        {"email": user.email, "company_id": user.company_id},
        {"employee_id": 1, "_id": 0}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="No employee record found")
    
    from services.time_service import time_service
    
    event = await time_service.end_break(
        employee_id=employee["employee_id"],
        company_id=user.company_id
    )
    return event.to_dict()


@router.get("/status")
async def get_clock_status(
    employee_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get current clock status for an employee"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not employee_id:
        employee = await db.employees.find_one(
            {"email": user.email, "company_id": user.company_id},
            {"employee_id": 1, "_id": 0}
        )
        if employee:
            employee_id = employee["employee_id"]
        else:
            # Return graceful "not clocked in" state for admins/owners with no employee record
            return {"status": "not_clocked_in", "employee_id": None, "last_event": None, "no_employee_record": True}

    from services.time_service import time_service

    try:
        status = await time_service.get_employee_status(employee_id)
        return status
    except Exception:
        return {"status": "not_clocked_in", "employee_id": employee_id, "last_event": None}


@router.get("/events")
async def get_clock_events(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user)
):
    """Get clock events for an employee"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    query = {"company_id": user.company_id}
    
    if employee_id:
        query["employee_id"] = employee_id
    
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" not in query:
            query["timestamp"] = {}
        query["timestamp"]["$lte"] = end_date + "T23:59:59"
    
    events = await db.clock_events.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"events": events, "total": len(events)}


# ==================== SHIFT ROUTES ====================

@router.post("/shifts")
async def create_shift(
    request_data: CreateShiftRequest,
    user: User = Depends(require_manager)
):
    """Create a new shift"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    try:
        shift = await time_service.create_shift(
            company_id=user.company_id,
            employee_id=request_data.employee_id,
            shift_date=date.fromisoformat(request_data.date),
            start_time=datetime.fromisoformat(request_data.start_time),
            end_time=datetime.fromisoformat(request_data.end_time),
            break_duration_minutes=request_data.break_duration_minutes,
            role=request_data.role,
            location=request_data.location,
            rota_id=request_data.rota_id,
            notes=request_data.notes
        )
        return shift.to_dict()
    except Exception as e:
        logger.error(f"Shift creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shifts")
async def get_shifts(
    start_date: str,
    end_date: str,
    employee_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get shifts within a date range"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    shifts = await time_service.get_shifts(
        company_id=user.company_id,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        employee_id=employee_id
    )
    
    return {"shifts": shifts, "total": len(shifts)}


@router.put("/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    request_data: UpdateShiftRequest,
    user: User = Depends(require_manager)
):
    """Update a shift"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    updates = request_data.dict(exclude_unset=True)
    
    try:
        result = await time_service.update_shift(shift_id, updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    user: User = Depends(require_manager)
):
    """Delete a shift"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    try:
        result = await time_service.delete_shift(shift_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== ROTA ROUTES ====================

@router.post("/rotas")
async def create_rota(
    request_data: CreateRotaRequest,
    user: User = Depends(require_manager)
):
    """Create a new rota"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    week_start = date.fromisoformat(request_data.week_start_date)
    
    # Validate it's a Monday
    if week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="Week start date must be a Monday")
    
    from services.time_service import time_service
    
    rota = await time_service.create_rota(
        company_id=user.company_id,
        name=request_data.name,
        week_start_date=week_start,
        created_by=user.user_id
    )
    
    return rota.to_dict()


@router.get("/rotas")
async def get_rotas(
    status: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get rotas for the company"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    rotas = await time_service.get_rotas(
        company_id=user.company_id,
        status=status
    )
    
    return {"rotas": rotas, "total": len(rotas)}


@router.post("/rotas/{rota_id}/publish")
async def publish_rota(
    rota_id: str,
    user: User = Depends(require_manager)
):
    """Publish a rota"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    try:
        result = await time_service.publish_rota(rota_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rotas/{rota_id}/copy")
async def copy_rota(
    rota_id: str,
    request_data: CopyRotaRequest,
    user: User = Depends(require_manager)
):
    """Copy a rota to a new week"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    new_week_start = date.fromisoformat(request_data.new_week_start_date)
    
    if new_week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="New week start date must be a Monday")
    
    from services.time_service import time_service
    
    try:
        rota = await time_service.copy_rota(
            rota_id=rota_id,
            new_week_start_date=new_week_start,
            created_by=user.user_id
        )
        return rota.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== TIMESHEET ROUTES ====================

@router.post("/timesheets/generate")
async def generate_timesheet(
    week_start_date: str,
    employee_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Generate a timesheet from clock events"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not employee_id:
        employee = await db.employees.find_one(
            {"email": user.email, "company_id": user.company_id},
            {"employee_id": 1, "_id": 0}
        )
        if employee:
            employee_id = employee["employee_id"]
        else:
            raise HTTPException(status_code=404, detail="No employee record found")
    
    week_start = date.fromisoformat(week_start_date)
    
    from services.time_service import time_service
    
    timesheet = await time_service.generate_timesheet(
        employee_id=employee_id,
        company_id=user.company_id,
        week_start_date=week_start
    )
    
    return timesheet.to_dict()


@router.get("/timesheets")
async def get_timesheets(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get timesheets"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    timesheets = await time_service.get_timesheets(
        company_id=user.company_id,
        employee_id=employee_id,
        status=status,
        limit=limit
    )
    
    return {"timesheets": timesheets, "total": len(timesheets)}


@router.get("/timesheets/pending")
async def get_pending_timesheets(user: User = Depends(require_manager)):
    """Get timesheets pending approval"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    timesheets = await time_service.get_pending_approvals(user.company_id)
    
    return {"timesheets": timesheets, "total": len(timesheets)}


@router.post("/timesheets/{timesheet_id}/submit")
async def submit_timesheet(
    timesheet_id: str,
    user: User = Depends(get_current_user)
):
    """Submit a timesheet for approval"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    employee = await db.employees.find_one(
        {"email": user.email, "company_id": user.company_id},
        {"employee_id": 1, "_id": 0}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="No employee record found")
    
    from services.time_service import time_service
    
    try:
        result = await time_service.submit_timesheet(
            timesheet_id=timesheet_id,
            employee_id=employee["employee_id"]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/timesheets/{timesheet_id}/approve")
async def approve_timesheet(
    timesheet_id: str,
    user: User = Depends(require_manager)
):
    """Approve a timesheet"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    try:
        result = await time_service.approve_timesheet(
            timesheet_id=timesheet_id,
            approved_by=user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/timesheets/{timesheet_id}/reject")
async def reject_timesheet(
    timesheet_id: str,
    request_data: TimesheetActionRequest,
    user: User = Depends(require_manager)
):
    """Reject a timesheet"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not request_data.reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    from services.time_service import time_service
    
    try:
        result = await time_service.reject_timesheet(
            timesheet_id=timesheet_id,
            rejected_by=user.user_id,
            reason=request_data.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== REPORTS ====================

@router.get("/reports/attendance")
async def get_attendance_report(
    start_date: str,
    end_date: str,
    user: User = Depends(require_manager)
):
    """Get attendance summary report"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.time_service import time_service
    
    summary = await time_service.get_attendance_summary(
        company_id=user.company_id,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date)
    )
    
    return summary
