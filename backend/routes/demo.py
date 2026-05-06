"""Demo Tour: seed demo data, drive guided walkthrough, and reset."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import os, sys, uuid, jwt, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Tour"])


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


DEMO_EMPLOYEES = [
    {"first_name": "Aarav", "last_name": "Patel", "job_title": "Senior Engineer", "department": "Engineering", "salary": 72000, "ni_number": "AB123456C", "tax_code": "1257L", "ni_letter": "A"},
    {"first_name": "Olivia", "last_name": "Williams", "job_title": "Product Manager", "department": "Product", "salary": 68000, "ni_number": "CD234567E", "tax_code": "1257L", "ni_letter": "A"},
    {"first_name": "James", "last_name": "Singh", "job_title": "Designer", "department": "Design", "salary": 52000, "ni_number": "EF345678F", "tax_code": "1257L", "ni_letter": "A"},
    {"first_name": "Sofia", "last_name": "Garcia", "job_title": "Sales Lead", "department": "Sales", "salary": 58000, "ni_number": "GH456789J", "tax_code": "1257L", "ni_letter": "A", "immigration_status": {"visa_type": "skilled_worker", "visa_end_date": (datetime.now(timezone.utc) + timedelta(days=180)).isoformat(), "sponsored": True, "cos_reference": "C2X4F7K"}},
    {"first_name": "Noah", "last_name": "Smith", "job_title": "HR Coordinator", "department": "HR", "salary": 38000, "ni_number": "JK567890K", "tax_code": "1257L", "ni_letter": "A"},
    {"first_name": "Maya", "last_name": "Chen", "job_title": "Finance Analyst", "department": "Finance", "salary": 56000, "ni_number": "LM678901N", "tax_code": "1257L", "ni_letter": "A"},
]


@router.post("/seed")
async def seed_demo(user: CurrentUser = Depends(get_current_user)):
    """Idempotently seed demo data for the current company"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    company_id = user.company_id
    now = datetime.now(timezone.utc)

    # Mark this company as a demo
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {
            "demo_mode": True,
            "demo_seeded_at": now.isoformat(),
            "paye_reference": "120/AB1234",
            "accounts_office_reference": "120PA00012345",
            "small_employer_relief": True,
        }}
    )

    created_employees = []
    for spec in DEMO_EMPLOYEES:
        existing = await db.employees.find_one({"company_id": company_id, "email": f"demo.{spec['first_name'].lower()}@realtouchhr-demo.uk"}, {"_id": 0})
        if existing:
            created_employees.append(existing["employee_id"])
            continue
        emp_id = f"emp_{uuid.uuid4().hex[:12]}"
        doc = {
            "employee_id": emp_id,
            "company_id": company_id,
            "email": f"demo.{spec['first_name'].lower()}@realtouchhr-demo.uk",
            "status": "active",
            "compliance_score": 100,
            "compliance_issues": [],
            "bank_account": "12345678",
            "bank_sort_code": "12-34-56",
            "start_date": (now - timedelta(days=420)).strftime("%Y-%m-%d"),
            "demo_seeded": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            **spec,
        }
        await db.employees.insert_one(doc)
        created_employees.append(emp_id)

    # Create a sample pay run
    payrun_id = f"payrun_{uuid.uuid4().hex[:12]}"
    today = now.date()
    start_d = today.replace(day=1)
    end_d = (start_d + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    pay_date = end_d
    total_gross = total_tax = total_ni = total_net = 0.0
    payslips_to_insert = []
    for spec, emp_id in zip(DEMO_EMPLOYEES, created_employees):
        salary = spec["salary"]
        monthly = salary / 12
        tax = max(0, (monthly - 1048) * 0.20)
        ni = max(0, (monthly - 797) * 0.12)
        pension = monthly * 0.05
        net = monthly - tax - ni - pension
        total_gross += monthly; total_tax += tax; total_ni += ni; total_net += net
        payslips_to_insert.append({
            "payrun_id": payrun_id,
            "employee_id": emp_id,
            "employee_name": f"{spec['first_name']} {spec['last_name']}",
            "gross_pay": round(monthly, 2),
            "tax_deduction": round(tax, 2),
            "ni_deduction": round(ni, 2),
            "pension_deduction": round(pension, 2),
            "other_deductions": 0,
            "net_pay": round(net, 2),
            "overtime_pay": 0,
            "demo_seeded": True,
        })

    # Idempotency: skip if a demo payrun already exists for this period
    existing_pr = await db.pay_runs.find_one(
        {"company_id": company_id, "demo_seeded": True},
        {"_id": 0}
    )
    if not existing_pr:
        await db.pay_runs.insert_one({
            "payrun_id": payrun_id,
            "company_id": company_id,
            "period_start": start_d.isoformat(),
            "period_end": end_d.isoformat(),
            "pay_date": pay_date.isoformat(),
            "status": "draft",
            "total_gross": round(total_gross, 2),
            "total_tax": round(total_tax, 2),
            "total_ni": round(total_ni, 2),
            "total_net": round(total_net, 2),
            "employee_count": len(DEMO_EMPLOYEES),
            "compliance_score": 100,
            "created_by": user.user_id,
            "demo_seeded": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        })
        if payslips_to_insert:
            await db.payslips.insert_many(payslips_to_insert)

    # Sample leave request and timesheet
    if not await db.leave_requests.find_one({"company_id": company_id, "demo_seeded": True}):
        await db.leave_requests.insert_one({
            "leave_id": f"leave_{uuid.uuid4().hex[:12]}",
            "employee_id": created_employees[0],
            "company_id": company_id,
            "leave_type": "Annual",
            "start_date": (today + timedelta(days=14)).isoformat(),
            "end_date": (today + timedelta(days=18)).isoformat(),
            "days": 5,
            "reason": "Summer holiday",
            "status": "pending",
            "demo_seeded": True,
            "created_at": now.isoformat(),
        })

    return {
        "status": "seeded",
        "company_id": company_id,
        "employee_count": len(created_employees),
        "payrun_id": payrun_id,
        "tour_steps": [
            {"id": "dashboard", "title": "Compliance Dashboard", "route": "/dashboard", "description": "Your real-time compliance score and critical actions."},
            {"id": "employees", "title": "Employees", "route": "/employees", "description": "Six demo employees across departments — including a sponsored worker."},
            {"id": "payroll", "title": "Payroll Preview", "route": "/payroll", "description": "A draft pay run is ready to review."},
            {"id": "statutory", "title": "Statutory Pay", "route": "/statutory", "description": "SSP / SMP / SPP / ShPP / SAP calculator for any employee."},
            {"id": "ukvi", "title": "UKVI Compliance", "route": "/ukvi", "description": "Visa expiry alerts and salary threshold monitoring."},
            {"id": "billing", "title": "Stripe Billing", "route": "/billing", "description": "Try a Stripe test checkout — card 4242 4242 4242 4242."},
        ]
    }


@router.post("/reset")
async def reset_demo(user: CurrentUser = Depends(get_current_user)):
    """Remove all demo-seeded data for this company"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    company_id = user.company_id
    counts = {}
    for col in ["employees", "pay_runs", "payslips", "leave_requests", "timesheets",
                "shifts", "ukvi_alerts", "compliance_tasks"]:
        result = await db[col].delete_many({"company_id": company_id, "demo_seeded": True})
        counts[col] = result.deleted_count
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"demo_mode": False}, "$unset": {"demo_seeded_at": ""}}
    )
    return {"status": "reset", "deleted": counts}


@router.get("/status")
async def demo_status(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        return {"demo_mode": False}
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0}) or {}
    emp_count = await db.employees.count_documents(
        {"company_id": user.company_id, "demo_seeded": True}
    )
    return {
        "demo_mode": company.get("demo_mode", False),
        "demo_seeded_at": company.get("demo_seeded_at"),
        "demo_employee_count": emp_count,
    }
