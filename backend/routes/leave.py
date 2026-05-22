"""
RealtouchHR - Leave Management Routes
Extracted from server.py during iter-13 refactor.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import uuid
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(tags=["Leave"])


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


@router.post("/leave", response_model=LeaveRequest)
async def create_leave_request(data: LeaveRequestCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    leave_id = f"leave_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    start = datetime.fromisoformat(data.start_date)
    end = datetime.fromisoformat(data.end_date)
    days = (end - start).days + 1

    leave_doc = {
        "leave_id": leave_id,
        "employee_id": user.user_id,
        "company_id": user.company_id,
        "leave_type": data.leave_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "days": days,
        "reason": data.reason,
        "status": "pending",
        "created_at": now.isoformat(),
    }
    await db.leave_requests.insert_one(leave_doc)

    from services.audit_service import create_audit_entry
    await create_audit_entry(
        company_id=user.company_id, user_id=user.user_id, user_name=user.name,
        action="create", entity_type="leave", entity_id=leave_id,
        details={"type": data.leave_type, "days": days}
    )

    leave_doc["created_at"] = now
    return LeaveRequest(**leave_doc)


@router.get("/leave", response_model=List[LeaveRequest])
async def get_leave_requests(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        return []
    leaves = await db.leave_requests.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    for leave in leaves:
        if isinstance(leave.get("created_at"), str):
            leave["created_at"] = datetime.fromisoformat(leave["created_at"])
    return [LeaveRequest(**leave) for leave in leaves]


@router.put("/leave/{leave_id}")
async def update_leave_request(
    leave_id: str,
    data: dict,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    leave = await db.leave_requests.find_one(
        {"leave_id": leave_id, "company_id": user.company_id}, {"_id": 0}
    )
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    employee = await db.employees.find_one({"employee_id": leave["employee_id"]}, {"_id": 0})

    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
        from services.audit_service import create_notification
        from services.email_service import email_service, get_base_template
        if data["status"] == "approved":
            update_fields["approved_by"] = user.user_id
            await create_notification(
                user.company_id, leave["employee_id"],
                "Leave Request Approved",
                f"Your {leave['leave_type']} leave request from {leave['start_date']} to {leave['end_date']} has been approved.",
                "leave_approved", "leave", leave_id
            )
            if employee and employee.get("email"):
                html = get_base_template(
                    f"<h2 style='color:#111827;'>Your Leave Request Has Been Approved</h2>"
                    f"<p style='color:#374151;'>Great news! Your {leave['leave_type']} leave request has been approved.</p>"
                    f"<p style='color:#374151;'><strong>Dates:</strong> {leave['start_date']} to {leave['end_date']}<br>"
                    f"<strong>Days:</strong> {leave.get('days', 'N/A')}</p>"
                )
                await email_service.send_email(employee["email"], "Leave Request Approved - RealtouchHR", html)
        elif data["status"] == "rejected":
            await create_notification(
                user.company_id, leave["employee_id"],
                "Leave Request Rejected",
                f"Your {leave['leave_type']} leave request from {leave['start_date']} to {leave['end_date']} has been rejected.",
                "leave_rejected", "leave", leave_id
            )
            if employee and employee.get("email"):
                html = get_base_template(
                    f"<h2 style='color:#111827;'>Leave Request Not Approved</h2>"
                    f"<p style='color:#374151;'>Unfortunately, your {leave['leave_type']} leave request was not approved.</p>"
                    f"<p style='color:#374151;'><strong>Dates:</strong> {leave['start_date']} to {leave['end_date']}</p>"
                    f"<p style='color:#374151;'>Please contact your manager if you have any questions.</p>"
                )
                await email_service.send_email(employee["email"], "Leave Request Update - RealtouchHR", html)

    await db.leave_requests.update_one(
        {"leave_id": leave_id, "company_id": user.company_id}, {"$set": update_fields}
    )

    from services.audit_service import create_audit_entry
    await create_audit_entry(
        company_id=user.company_id, user_id=user.user_id, user_name=user.name,
        action="update", entity_type="leave", entity_id=leave_id, details=update_fields
    )
    return {"message": "Leave request updated"}
