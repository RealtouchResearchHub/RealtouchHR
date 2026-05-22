"""
RealtouchHR - Tax Documents Routes
Download P45 / P60 / P11D as PDF and manage P11D benefits records.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, date
import io, os, sys, logging
from pathlib import Path
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
JWT_ALGORITHM = "HS256"
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tax-docs", tags=["Tax Documents"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class P11DBenefitItem(BaseModel):
    category: str = Field(..., description="e.g. company_car, medical_insurance")
    description: str
    cash_equivalent: float


class P11DCreateRequest(BaseModel):
    employee_id: str
    tax_year: str
    benefits: List[P11DBenefitItem]


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


async def _get_employee_and_company(employee_id: str, company_id: str):
    emp = await db.employees.find_one({"employee_id": employee_id, "company_id": company_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0}) or {}
    return emp, company


def _tax_year_bounds(tax_year: str):
    """Return (start_date, end_date) for a UK tax year like '2024-25'."""
    try:
        start_year = int(tax_year.split("-")[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid tax year format, use e.g. '2024-25'")
    return date(start_year, 4, 6), date(start_year + 1, 4, 5)


async def _gate_or_402(company_id: str, user_id: str, resource_id: str):
    """Apply trial + £5 paywall + quota + bulk-pass gate. Returns access dict if allowed, raises HTTPException otherwise."""
    from services.trial_service import download_gate
    access = await download_gate.check_access(company_id, user_id, resource_id)
    if not access.get("allowed"):
        raise HTTPException(
            status_code=402 if access.get("needs_payment") else 403,
            detail=access.get("reason", "Download not allowed")
        )
    if access.get("pass_id"):
        await download_gate.consume_pass(access["pass_id"])
    elif access.get("plan_quota_consume"):
        await download_gate.consume_quota(company_id, access["month_key"])
    return access


# ==================== P45 ====================

@router.get("/p45/{employee_id}")
async def download_p45(employee_id: str, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    emp, company = await _get_employee_and_company(employee_id, user.company_id)

    # Gate
    await _gate_or_402(user.company_id, user.user_id, f"p45:{employee_id}")

    # Fetch the most recent P45 record generated during termination
    p45_doc = await db.tax_documents.find_one(
        {"employee_id": employee_id, "company_id": user.company_id, "document_type": "p45"},
        {"_id": 0},
        sort=[("generated_at", -1)]
    )

    # If no P45 exists yet but employee is terminated, generate one on the fly
    if not p45_doc:
        if emp.get("status") != "terminated":
            raise HTTPException(status_code=400, detail="P45 only available for terminated employees")
        # Build minimal P45 data
        p45_data = {
            "leaving_date": emp.get("leaving_date", ""),
            "tax_code": emp.get("tax_code", ""),
            "week1_month1_basis": False,
            "total_pay_to_date": 0.0,
            "total_tax_to_date": 0.0,
            "student_loan_deductions": 0.0,
            "pay_this_employment": 0.0,
            "tax_this_employment": 0.0,
            "pay_previous_employment": 0.0,
            "tax_previous_employment": 0.0,
        }
    else:
        p45_data = p45_doc.get("data", {})

    from services.pdf_service import generate_p45_pdf
    pdf_bytes = generate_p45_pdf(emp, company, p45_data)

    emp_name = f"{emp.get('first_name', '')}_{emp.get('last_name', '')}".strip("_")
    filename = f"P45_{emp_name}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ==================== P60 ====================

async def _build_p60_data(employee_id: str, company_id: str, tax_year: str) -> Dict[str, Any]:
    """Aggregate pay/tax totals from payslips for the tax year"""
    start_d, end_d = _tax_year_bounds(tax_year)
    payslips = await db.payslips.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(2000)

    total_pay = 0.0
    total_tax = 0.0
    total_ni = 0.0
    total_student_loan = 0.0
    total_smp = 0.0
    total_spp = 0.0
    total_ssp = 0.0

    for ps in payslips:
        payrun = await db.pay_runs.find_one({"payrun_id": ps.get("payrun_id")}, {"_id": 0})
        if not payrun:
            continue
        try:
            pay_date = date.fromisoformat(payrun.get("pay_date", ""))
        except (ValueError, TypeError):
            continue
        if pay_date < start_d or pay_date > end_d:
            continue
        total_pay += ps.get("gross_pay", 0) or 0
        total_tax += ps.get("tax_deduction", 0) or 0
        total_ni += ps.get("ni_deduction", 0) or 0
        total_student_loan += ps.get("student_loan_deduction", 0) or 0
        total_smp += ps.get("smp", 0) or 0
        total_spp += ps.get("spp", 0) or 0
        total_ssp += ps.get("ssp", 0) or 0

    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0}) or {}

    return {
        "tax_year": tax_year,
        "tax_code": employee.get("tax_code", ""),
        "total_pay": round(total_pay, 2),
        "total_tax": round(total_tax, 2),
        "ni_letter": employee.get("ni_letter", "A"),
        "ni_contributions_breakdown": {
            "earnings_at_lel": 0,
            "earnings_lel_to_pt": 0,
            "earnings_pt_to_uel": 0,
            "employee_ni": round(total_ni, 2),
        },
        "student_loan_deductions": round(total_student_loan, 2),
        "statutory_maternity_pay": round(total_smp, 2),
        "statutory_paternity_pay": round(total_spp, 2),
        "statutory_sick_pay": round(total_ssp, 2),
        "pay_previous_employment": 0.0,
        "tax_previous_employment": 0.0,
    }


@router.get("/p60/{employee_id}")
async def download_p60(employee_id: str, tax_year: str = "2024-25", user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    emp, company = await _get_employee_and_company(employee_id, user.company_id)

    # Gate
    await _gate_or_402(user.company_id, user.user_id, f"p60:{employee_id}:{tax_year}")

    p60_data = await _build_p60_data(employee_id, user.company_id, tax_year)

    # Persist for audit
    await db.tax_documents.insert_one({
        "document_id": f"p60_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{employee_id[-6:]}",
        "employee_id": employee_id,
        "company_id": user.company_id,
        "document_type": "p60",
        "tax_year": tax_year,
        "data": p60_data,
        "generated_by": user.user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

    from services.pdf_service import generate_p60_pdf
    pdf_bytes = generate_p60_pdf(emp, company, p60_data)

    emp_name = f"{emp.get('first_name', '')}_{emp.get('last_name', '')}".strip("_")
    filename = f"P60_{emp_name}_{tax_year}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ==================== P11D ====================

@router.post("/p11d")
async def create_p11d(req: P11DCreateRequest, user: CurrentUser = Depends(get_current_user)):
    """Create/update a P11D benefits record for an employee"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    # Confirm employee exists
    await _get_employee_and_company(req.employee_id, user.company_id)

    now = datetime.now(timezone.utc).isoformat()
    benefits = [b.model_dump() for b in req.benefits]
    total_cash = sum(b["cash_equivalent"] for b in benefits)
    record = {
        "employee_id": req.employee_id,
        "company_id": user.company_id,
        "tax_year": req.tax_year,
        "benefits": benefits,
        "total_cash_equivalent": round(total_cash, 2),
        "class_1a_ni_due": round(total_cash * 0.138, 2),  # 13.8% Class 1A NI
        "updated_at": now,
    }
    await db.p11d_records.update_one(
        {"employee_id": req.employee_id, "company_id": user.company_id, "tax_year": req.tax_year},
        {"$set": record, "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    return {"message": "P11D record saved", **record}


@router.get("/p11d/{employee_id}/{tax_year}")
async def download_p11d(employee_id: str, tax_year: str, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    emp, company = await _get_employee_and_company(employee_id, user.company_id)

    # Gate
    await _gate_or_402(user.company_id, user.user_id, f"p11d:{employee_id}:{tax_year}")

    record = await db.p11d_records.find_one(
        {"employee_id": employee_id, "company_id": user.company_id, "tax_year": tax_year},
        {"_id": 0}
    )
    if not record:
        raise HTTPException(status_code=404, detail="No P11D record for this tax year")

    from services.pdf_service import generate_p11d_pdf
    pdf_bytes = generate_p11d_pdf(emp, company, {"tax_year": tax_year, "benefits": record.get("benefits", [])})

    emp_name = f"{emp.get('first_name', '')}_{emp.get('last_name', '')}".strip("_")
    filename = f"P11D_{emp_name}_{tax_year}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/p11d/{employee_id}")
async def get_employee_p11d_records(employee_id: str, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    records = await db.p11d_records.find(
        {"employee_id": employee_id, "company_id": user.company_id},
        {"_id": 0}
    ).sort("tax_year", -1).to_list(50)
    return {"records": records, "total": len(records)}


@router.get("/employee/{employee_id}/documents")
async def list_employee_tax_documents(employee_id: str, user: CurrentUser = Depends(get_current_user)):
    """Return all tax documents (P45/P60/P11D) generated for an employee"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    docs = await db.tax_documents.find(
        {"employee_id": employee_id, "company_id": user.company_id},
        {"_id": 0, "data": 0}
    ).sort("generated_at", -1).to_list(100)
    p11ds = await db.p11d_records.find(
        {"employee_id": employee_id, "company_id": user.company_id},
        {"_id": 0, "benefits": 0}
    ).sort("tax_year", -1).to_list(50)
    return {"documents": docs, "p11d_records": p11ds}
