"""Demo Tour: seed demo data, drive guided walkthrough, and reset."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import os, sys, uuid, jwt, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Tour"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


def _normalize_current_user_doc(user_doc: dict) -> dict:
    normalized = dict(user_doc)
    email = (normalized.get("email") or "").strip()
    normalized["name"] = (normalized.get("name") or email.split("@")[0] or "User").strip()
    return normalized


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
    return CurrentUser(**_normalize_current_user_doc(user_doc))


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
    """Idempotently seed demo data for the current company.
    If the user has no company yet, a demo company is auto-created so new
    users can try the tour without completing company setup first."""
    if not user.company_id:
        now = datetime.now(timezone.utc)
        company_id = f"company_demo_{uuid.uuid4().hex[:12]}"
        await db.companies.insert_one({
            "company_id": company_id,
            "name": f"{user.name}'s Demo Company",
            "industry": "Technology",
            "size": "10-50",
            "address": "1 Demo Street, London EC1A 1BB",
            "payroll_frequency": "monthly",
            "owner_id": user.user_id,
            "setup_completed": False,
            "demo_mode": True,
            "demo_seeded_at": now.isoformat(),
            "created_at": now.isoformat(),
            "paye_reference": "120/AB1234",
            "accounts_office_reference": "120PA00012345",
            "small_employer_relief": True,
        })
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": {"company_id": company_id}}
        )
        user = CurrentUser(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            role=user.role,
            company_id=company_id,
        )
    try:
        return await _do_seed(user)
    except Exception as exc:
        logger.warning("seed_demo error for %s: %s", user.company_id, exc)
        return {"status": "seeded", "company_id": user.company_id, "employee_count": 0, "payrun_id": None, "tour_steps": []}


async def _do_seed(user: CurrentUser):
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

    # Wire up demo org hierarchy (idempotent):
    # Order: [0] Aarav, [1] Olivia, [2] James, [3] Sofia, [4] Noah, [5] Maya
    # Olivia is the top. Aarav/Sofia/Noah/Maya report to Olivia. James reports to Aarav.
    if len(created_employees) == 6:
        aarav, olivia, james, sofia, noah, maya = created_employees
        for emp_id, mgr_id in [(aarav, olivia), (james, aarav), (sofia, olivia), (noah, olivia), (maya, olivia)]:
            await db.employees.update_one(
                {"employee_id": emp_id, "company_id": company_id},
                {"$set": {"line_manager_id": mgr_id}}
            )

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
            "payslip_id": f"ps_{uuid.uuid4().hex[:12]}",
            "payrun_id": payrun_id,
            "company_id": company_id,
            "employee_id": emp_id,
            "employee_name": f"{spec['first_name']} {spec['last_name']}",
            "gross_pay": round(monthly, 2),
            "income_tax": round(tax, 2),
            "national_insurance": round(ni, 2),
            "pension_ee": round(pension, 2),
            "net_pay": round(net, 2),
            "status": "draft",
            "created_at": now.isoformat(),
            "demo_seeded": True,
        })

    # Idempotency: skip if a demo payrun already exists for this period
    existing_pr = await db.pay_runs.find_one(
        {"company_id": company_id, "period_start": start_d.isoformat()},
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
    first_emp_id = created_employees[0] if created_employees else None
    if first_emp_id and not await db.leave_requests.find_one({"company_id": company_id, "employee_id": first_emp_id, "reason": "Summer holiday"}):
        demo_leave_id = f"leave_{uuid.uuid4().hex[:12]}"
        await db.leave_requests.insert_one({
            "leave_request_id": demo_leave_id,
            "leave_id": demo_leave_id,
            "employee_id": created_employees[0],
            "company_id": company_id,
            "employee_name": f"{DEMO_EMPLOYEES[0]['first_name']} {DEMO_EMPLOYEES[0]['last_name']}",
            "leave_type": "Annual",
            "start_date": (today + timedelta(days=14)).isoformat(),
            "end_date": (today + timedelta(days=18)).isoformat(),
            "days": 5,
            "reason": "Summer holiday",
            "status": "pending",
            "demo_seeded": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
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


@router.post("/sandbox")
async def create_sandbox_account():
    """Public, no-auth sandbox account creator: instantly returns a token that
    is bound to a fresh demo company, seeded with sample data. Used for the
    public landing page 'Try Demo' CTA — accounts auto-expire after 24h."""
    import secrets
    now = datetime.now(timezone.utc)
    suffix = secrets.token_hex(4)
    email = f"sandbox.{suffix}@realtouchhr-demo.uk"
    user_id = f"user_sandbox_{uuid.uuid4().hex[:12]}"
    company_id = f"company_sandbox_{uuid.uuid4().hex[:12]}"

    # Create company
    await db.companies.insert_one({
        "company_id": company_id,
        "name": "RealtouchHR Demo Co.",
        "industry": "Technology",
        "size": "10-50",
        "address": "1 Demo Street, London EC1A 1BB",
        "payroll_frequency": "monthly",
        "owner_id": user_id,
        "setup_completed": True,
        "demo_mode": True,
        "demo_seeded_at": now.isoformat(),
        "is_sandbox": True,
        "sandbox_expires_at": (now + timedelta(hours=24)).isoformat(),
        "created_at": now.isoformat(),
        "paye_reference": "120/AB1234",
        "accounts_office_reference": "120PA00012345",
        "small_employer_relief": True,
    })

    # Create user (no password)
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": "Sandbox Visitor",
        "role": "owner",
        "company_id": company_id,
        "is_sandbox": True,
        "sandbox_expires_at": (now + timedelta(hours=24)).isoformat(),
        "auth_method": "sandbox",
        "created_at": now.isoformat(),
        "preferences": {"theme_preference": "system"},
    })

    # Issue a JWT (24-hour life)
    token = jwt.encode(
        {"user_id": user_id, "email": email, "exp": now + timedelta(hours=24)},
        JWT_SECRET, algorithm="HS256"
    )

    # Persist a session so cookie auth also works
    await db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    })

    # Synthetic CurrentUser to seed demo data
    fake_user = CurrentUser(user_id=user_id, email=email, name="Sandbox Visitor", role="owner", company_id=company_id)
    try:
        await seed_demo(user=fake_user)
    except Exception as exc:
        logger.warning("seed_demo failed for sandbox %s: %s", company_id, exc)

    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "email": email,
            "name": "Sandbox Visitor",
            "role": "owner",
            "company_id": company_id,
            "auth_method": "sandbox",
        },
        "company_id": company_id,
        "expires_in_hours": 24,
        "tour_steps": [
            {"id": "dashboard", "title": "Compliance Dashboard", "route": "/dashboard", "description": "Your real-time compliance score and critical actions."},
            {"id": "employees", "title": "Employees", "route": "/employees", "description": "Six demo employees including a sponsored worker."},
            {"id": "payroll", "title": "Payroll Preview", "route": "/payroll", "description": "A draft pay run is ready to review."},
            {"id": "statutory", "title": "Statutory Pay", "route": "/statutory", "description": "Calculate SSP/SMP/SPP/ShPP/SAP for any employee."},
            {"id": "ukvi", "title": "UKVI Compliance", "route": "/ukvi", "description": "Visa expiry alerts and salary threshold monitoring."},
            {"id": "billing", "title": "Stripe Billing", "route": "/billing", "description": "Try a Stripe test checkout — card 4242 4242 4242 4242."},
        ]
    }


@router.post("/sandbox/cleanup")
async def cleanup_expired_sandboxes():
    """Delete sandbox companies + users + their data older than 24h. Idempotent."""
    now = datetime.now(timezone.utc)
    cutoff = now.isoformat()
    expired_companies = await db.companies.find(
        {"is_sandbox": True, "sandbox_expires_at": {"$lt": cutoff}},
        {"_id": 0, "company_id": 1, "owner_id": 1}
    ).to_list(1000)
    deleted = {"companies": 0, "employees": 0, "pay_runs": 0, "payslips": 0, "users": 0, "leave_requests": 0, "user_sessions": 0}
    for c in expired_companies:
        cid = c["company_id"]
        for col, key in [
            ("employees", "company_id"),
            ("pay_runs", "company_id"),
            ("leave_requests", "company_id"),
            ("ukvi_alerts", "company_id"),
            ("compliance_tasks", "company_id"),
            ("audit_log", "company_id"),
            ("ukvi_reports", "company_id"),
            ("payslips", None),  # via payrun join
        ]:
            if col == "payslips":
                payruns = await db.pay_runs.find({"company_id": cid}, {"_id": 0, "payrun_id": 1}).to_list(1000)
                ids = [p["payrun_id"] for p in payruns]
                if ids:
                    res = await db.payslips.delete_many({"payrun_id": {"$in": ids}})
                    deleted["payslips"] += res.deleted_count
            else:
                res = await db[col].delete_many({key: cid})
                if col in deleted:
                    deleted[col] += res.deleted_count
        # Delete owner user + sessions
        if c.get("owner_id"):
            res = await db.users.delete_many({"user_id": c["owner_id"]})
            deleted["users"] += res.deleted_count
            res = await db.user_sessions.delete_many({"user_id": c["owner_id"]})
            deleted["user_sessions"] += res.deleted_count
    res = await db.companies.delete_many({"is_sandbox": True, "sandbox_expires_at": {"$lt": cutoff}})
    deleted["companies"] = res.deleted_count
    return {"cleaned_up": len(expired_companies), "deleted": deleted}


@router.post("/reset")
async def reset_demo(user: CurrentUser = Depends(get_current_user)):
    """Remove all demo-seeded data for this company"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    company_id = user.company_id
    counts = {}

    # Delete demo employees (identified by email domain)
    demo_emps = await db.employees.find(
        {"company_id": company_id, "email": {"$regex": "realtouchhr-demo.uk"}},
        {"_id": 0}
    ).to_list(1000)
    demo_emp_ids = [e["employee_id"] for e in demo_emps if e.get("employee_id")]

    emp_res = await db.employees.delete_many(
        {"company_id": company_id, "email": {"$regex": "realtouchhr-demo.uk"}}
    )
    counts["employees"] = emp_res.deleted_count

    # Delete leave requests for demo employees
    lr_count = 0
    for eid in demo_emp_ids:
        res = await db.leave_requests.delete_many({"company_id": company_id, "employee_id": eid})
        lr_count += res.deleted_count
    counts["leave_requests"] = lr_count

    # Delete demo pay runs (current-month period_start) and their payslips
    today = datetime.now(timezone.utc).date()
    demo_period_start = today.replace(day=1).isoformat()
    demo_runs = await db.pay_runs.find(
        {"company_id": company_id, "period_start": demo_period_start},
        {"_id": 0}
    ).to_list(100)
    demo_run_ids = [r["payrun_id"] for r in demo_runs if r.get("payrun_id")]

    pr_count = 0
    ps_count = 0
    for rid in demo_run_ids:
        res = await db.payslips.delete_many({"payrun_id": rid})
        ps_count += res.deleted_count
        res = await db.pay_runs.delete_one({"payrun_id": rid})
        pr_count += res.deleted_count
    counts["pay_runs"] = pr_count
    counts["payslips"] = ps_count

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
        {"company_id": user.company_id, "email": {"$regex": "realtouchhr-demo.uk"}}
    )
    return {
        "demo_mode": company.get("demo_mode", False),
        "demo_seeded_at": company.get("demo_seeded_at"),
        "demo_employee_count": emp_count,
    }
