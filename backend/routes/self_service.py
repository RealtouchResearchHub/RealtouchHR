"""
RealtouchHR - Employee Self-Service Routes
Portal for employees to view payslips, request leave, update details
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional
import io
import logging

from models import (
    User, SelfServiceProfile, SelfServicePayslip, SelfServiceProfileUpdate,
    LeaveRequest, LeaveRequestCreate, LeaveBalance
)
from utils import db, generate_leave_id, now_utc, now_iso, days_between
from routes.auth import get_current_user
from services.email_service import email_service, leave_approval_email

logger = logging.getLogger(__name__)

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
