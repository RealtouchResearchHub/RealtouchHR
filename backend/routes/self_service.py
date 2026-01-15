"""
RealtouchHR - Employee Self-Service Routes
Portal for employees to view payslips, request leave, update details
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional
import io
import logging
import os
import sys
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, ConfigDict
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

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "owner"
    company_id: Optional[str] = None
    employee_id: Optional[str] = None
    theme_preference: str = "light"
    created_at: datetime

class SelfServiceProfile(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    can_edit_personal: bool = True
    can_view_payslips: bool = True
    can_request_leave: bool = True

class SelfServicePayslip(BaseModel):
    payrun_id: str
    period_start: str
    period_end: str
    pay_date: str
    gross_pay: float
    net_pay: float
    status: str

class SelfServiceProfileUpdate(BaseModel):
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    bank_account: Optional[str] = None
    bank_sort_code: Optional[str] = None

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: str
    end_date: str
    reason: Optional[str] = None

class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    leave_id: str
    employee_id: str
    company_id: str
    leave_type: str
    start_date: str
    end_date: str
    days: int
    reason: Optional[str] = None
    status: str = "pending"
    approved_by: Optional[str] = None
    created_at: datetime

class LeaveBalance(BaseModel):
    employee_id: str
    year: int
    annual_entitlement: int = 28
    used: int = 0
    pending: int = 0
    remaining: int = 28

# ==================== HELPERS ====================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_leave_id() -> str:
    return f"leave_{uuid.uuid4().hex[:12]}"

def days_between(start_date: str, end_date: str) -> int:
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return (end - start).days + 1

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
            if isinstance(user_doc.get("created_at"), str):
                user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)

router = APIRouter(prefix="/self-service", tags=["Employee Self-Service"])


# ==================== HELPERS ====================

async def get_employee_for_user(user: User) -> dict:
    """Get employee record linked to user"""
    if user.employee_id:
        employee = await db.employees.find_one(
            {"employee_id": user.employee_id},
            {"_id": 0}
        )
        if employee:
            return employee
    
    # Try to find by email
    employee = await db.employees.find_one(
        {"email": user.email, "enable_self_service": True},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(
            status_code=403,
            detail="No employee record linked to your account. Please contact HR."
        )
    
    return employee


# ==================== PROFILE ====================

@router.get("/profile", response_model=SelfServiceProfile)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Get own employee profile"""
    employee = await get_employee_for_user(user)
    
    return SelfServiceProfile(
        employee_id=employee["employee_id"],
        first_name=employee.get("first_name", ""),
        last_name=employee.get("last_name", ""),
        email=employee.get("email", ""),
        job_title=employee.get("job_title"),
        department=employee.get("department"),
        start_date=employee.get("start_date"),
        can_edit_personal=True,
        can_view_payslips=True,
        can_request_leave=True
    )


@router.put("/profile")
async def update_my_profile(
    data: SelfServiceProfileUpdate,
    user: User = Depends(get_current_user)
):
    """Update own profile - limited fields"""
    employee = await get_employee_for_user(user)
    
    # Only allow updating specific fields
    update_fields = {}
    if data.phone is not None:
        update_fields["phone"] = data.phone
    if data.address is not None:
        update_fields["address"] = data.address
    if data.emergency_contact_name is not None:
        update_fields["emergency_contact_name"] = data.emergency_contact_name
    if data.emergency_contact_phone is not None:
        update_fields["emergency_contact_phone"] = data.emergency_contact_phone
    if data.bank_account is not None:
        update_fields["bank_account"] = data.bank_account
    if data.bank_sort_code is not None:
        update_fields["bank_sort_code"] = data.bank_sort_code
    
    if update_fields:
        update_fields["updated_at"] = now_iso()
        await db.employees.update_one(
            {"employee_id": employee["employee_id"]},
            {"$set": update_fields}
        )
        
        # Create audit entry
        await db.audit_log.insert_one({
            "audit_id": f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "company_id": employee.get("company_id"),
            "user_id": user.user_id,
            "user_name": user.name,
            "action": "self_service_update",
            "entity_type": "employee",
            "entity_id": employee["employee_id"],
            "details": {"fields_updated": list(update_fields.keys())},
            "timestamp": now_iso()
        })
    
    return {"message": "Profile updated successfully"}


# ==================== PAYSLIPS ====================

@router.get("/payslips", response_model=List[SelfServicePayslip])
async def get_my_payslips(
    limit: int = 12,
    user: User = Depends(get_current_user)
):
    """Get own payslips"""
    employee = await get_employee_for_user(user)
    
    # Get payslips for this employee
    payslips = await db.payslips.find(
        {"employee_id": employee["employee_id"]},
        {"_id": 0}
    ).sort("pay_date", -1).limit(limit).to_list(limit)
    
    result = []
    for ps in payslips:
        # Get pay run details
        payrun = await db.pay_runs.find_one(
            {"payrun_id": ps.get("payrun_id")},
            {"_id": 0}
        )
        if payrun:
            result.append(SelfServicePayslip(
                payrun_id=ps.get("payrun_id", ""),
                period_start=payrun.get("period_start", ""),
                period_end=payrun.get("period_end", ""),
                pay_date=payrun.get("pay_date", ""),
                gross_pay=ps.get("gross_pay", 0),
                net_pay=ps.get("net_pay", 0),
                status=payrun.get("status", "")
            ))
    
    return result


@router.get("/payslips/{payrun_id}/download")
async def download_my_payslip(
    payrun_id: str,
    user: User = Depends(get_current_user)
):
    """Download own payslip as PDF"""
    employee = await get_employee_for_user(user)
    
    # Get payslip
    payslip = await db.payslips.find_one(
        {"payrun_id": payrun_id, "employee_id": employee["employee_id"]},
        {"_id": 0}
    )
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    # Get pay run
    payrun = await db.pay_runs.find_one({"payrun_id": payrun_id}, {"_id": 0})
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": employee.get("company_id")},
        {"_id": 0}
    )
    
    # Generate PDF
    from services.pdf_service import generate_payslip_pdf
    pdf_bytes = generate_payslip_pdf(payslip, company, payrun, employee)
    
    filename = f"payslip_{employee['last_name']}_{payrun['period_end']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== LEAVE ====================

@router.get("/leave/balance", response_model=LeaveBalance)
async def get_my_leave_balance(user: User = Depends(get_current_user)):
    """Get own leave balance"""
    employee = await get_employee_for_user(user)
    
    current_year = datetime.now().year
    
    # Get leave balance record
    balance = await db.leave_balances.find_one(
        {"employee_id": employee["employee_id"], "year": current_year},
        {"_id": 0}
    )
    
    if not balance:
        # Calculate from leave requests
        approved_leave = await db.leave_requests.find({
            "employee_id": employee["employee_id"],
            "status": "approved",
            "start_date": {"$regex": f"^{current_year}"}
        }, {"_id": 0}).to_list(100)
        
        pending_leave = await db.leave_requests.find({
            "employee_id": employee["employee_id"],
            "status": "pending",
            "start_date": {"$regex": f"^{current_year}"}
        }, {"_id": 0}).to_list(100)
        
        used = sum(l.get("days", 0) for l in approved_leave)
        pending = sum(l.get("days", 0) for l in pending_leave)
        
        balance = {
            "employee_id": employee["employee_id"],
            "year": current_year,
            "annual_entitlement": 28,  # UK statutory minimum
            "used": used,
            "pending": pending,
            "remaining": 28 - used
        }
    
    return LeaveBalance(**balance)


@router.get("/leave/requests", response_model=List[LeaveRequest])
async def get_my_leave_requests(
    status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get own leave requests"""
    employee = await get_employee_for_user(user)
    
    query = {"employee_id": employee["employee_id"]}
    if status:
        query["status"] = status
    
    leaves = await db.leave_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for leave in leaves:
        if isinstance(leave.get("created_at"), str):
            leave["created_at"] = datetime.fromisoformat(leave["created_at"])
    
    return [LeaveRequest(**leave) for leave in leaves]


@router.post("/leave/request", response_model=LeaveRequest)
async def request_leave(
    data: LeaveRequestCreate,
    user: User = Depends(get_current_user)
):
    """Submit a new leave request"""
    employee = await get_employee_for_user(user)
    
    leave_id = generate_leave_id()
    now = now_utc()
    
    # Calculate days
    days = days_between(data.start_date, data.end_date)
    
    # Check balance
    balance = await get_my_leave_balance(user)
    if days > balance.remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient leave balance. You have {balance.remaining} days remaining."
        )
    
    leave_doc = {
        "leave_id": leave_id,
        "employee_id": employee["employee_id"],
        "company_id": employee.get("company_id"),
        "leave_type": data.leave_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "days": days,
        "reason": data.reason,
        "status": "pending",
        "created_at": now.isoformat()
    }
    await db.leave_requests.insert_one(leave_doc)
    
    # Notify managers
    managers = await db.users.find(
        {
            "company_id": employee.get("company_id"),
            "role": {"$in": ["owner", "admin", "hr_manager", "manager"]}
        },
        {"_id": 0, "email": 1, "name": 1}
    ).to_list(10)
    
    # Create notifications for managers
    for manager in managers:
        await db.notifications.insert_one({
            "notification_id": f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}_{manager.get('email', '').split('@')[0]}",
            "company_id": employee.get("company_id"),
            "user_id": manager.get("user_id", ""),
            "title": "New Leave Request",
            "message": f"{employee['first_name']} {employee['last_name']} has requested {days} day(s) of {data.leave_type} leave.",
            "notification_type": "leave_request",
            "entity_type": "leave",
            "entity_id": leave_id,
            "read": False,
            "created_at": now.isoformat()
        })
    
    leave_doc["created_at"] = now
    return LeaveRequest(**leave_doc)


@router.delete("/leave/request/{leave_id}")
async def cancel_leave_request(
    leave_id: str,
    user: User = Depends(get_current_user)
):
    """Cancel a pending leave request"""
    employee = await get_employee_for_user(user)
    
    # Get leave request
    leave = await db.leave_requests.find_one(
        {"leave_id": leave_id, "employee_id": employee["employee_id"]},
        {"_id": 0}
    )
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending requests can be cancelled"
        )
    
    await db.leave_requests.update_one(
        {"leave_id": leave_id},
        {"$set": {"status": "cancelled"}}
    )
    
    return {"message": "Leave request cancelled"}


# ==================== DOCUMENTS ====================

@router.get("/documents")
async def get_my_documents(user: User = Depends(get_current_user)):
    """Get documents shared with employee"""
    employee = await get_employee_for_user(user)
    
    # Get documents for this employee
    docs = await db.documents.find(
        {
            "$or": [
                {"employee_id": employee["employee_id"]},
                {"employee_id": None, "company_id": employee.get("company_id")}  # Company-wide docs
            ]
        },
        {"_id": 0, "content": 0}  # Exclude content in list
    ).sort("created_at", -1).to_list(100)
    
    return docs


@router.get("/documents/{document_id}")
async def get_my_document(
    document_id: str,
    user: User = Depends(get_current_user)
):
    """Get a specific document"""
    employee = await get_employee_for_user(user)
    
    doc = await db.documents.find_one(
        {
            "document_id": document_id,
            "$or": [
                {"employee_id": employee["employee_id"]},
                {"employee_id": None, "company_id": employee.get("company_id")}
            ]
        },
        {"_id": 0}
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc
