"""Year-end Close: P60 batch, EPS auto-generate, FPS final indicator."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, date
from pathlib import Path
import os, sys, uuid, logging, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/year-end", tags=["Year End"])


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


def _bounds(tax_year: str):
    try:
        sy = int(tax_year.split("-")[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid tax year (use 2024-25)")
    return date(sy, 4, 6), date(sy + 1, 4, 5)


@router.get("/preview")
async def preview_year_end(tax_year: str = "2024-25", user: CurrentUser = Depends(get_current_user)):
    """Preview year-end totals: P60 count, EPS recovery summary, FPS final-flag candidates."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    start_d, end_d = _bounds(tax_year)
    company_id = user.company_id

    employees = await db.employees.find({"company_id": company_id}, {"_id": 0}).to_list(5000)
    payslip_count = 0
    total_pay = 0.0
    total_tax = 0.0
    total_ni = 0.0
    last_fps = None

    for emp in employees:
        ps = await db.payslips.find({"employee_id": emp["employee_id"]}, {"_id": 0}).to_list(2000)
        for p in ps:
            payrun = await db.pay_runs.find_one({"payrun_id": p.get("payrun_id")}, {"_id": 0})
            if not payrun:
                continue
            try:
                pd = date.fromisoformat(payrun.get("pay_date", ""))
            except (ValueError, TypeError):
                continue
            if start_d <= pd <= end_d:
                payslip_count += 1
                total_pay += p.get("gross_pay", 0) or 0
                total_tax += p.get("tax_deduction", 0) or 0
                total_ni += p.get("ni_deduction", 0) or 0
                if last_fps is None or pd > last_fps:
                    last_fps = pd

    # EPS recovery preview from statutory service
    from services.statutory_service import statutory_service
    eps = await statutory_service.get_eps_recovery_summary(company_id, 12, tax_year)

    return {
        "tax_year": tax_year,
        "tax_year_start": start_d.isoformat(),
        "tax_year_end": end_d.isoformat(),
        "p60_eligible_employees": len([e for e in employees if e.get("status") != "terminated"]),
        "payslip_count": payslip_count,
        "total_pay": round(total_pay, 2),
        "total_tax": round(total_tax, 2),
        "total_ni": round(total_ni, 2),
        "eps_recovery": eps.get("recovery"),
        "last_pay_date_in_year": last_fps.isoformat() if last_fps else None,
        "ready_for_year_end": last_fps is not None and last_fps <= end_d,
    }


@router.post("/close")
async def close_year_end(tax_year: str = "2024-25", user: CurrentUser = Depends(get_current_user)):
    """Mark final FPS, queue P60 generation for all active employees, generate EPS submission record."""
    if user.role not in ("owner", "admin", "payroll_admin"):
        raise HTTPException(status_code=403, detail="You do not have permission to close the payroll year")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    company_id = user.company_id
    now = datetime.now(timezone.utc).isoformat()

    employees = await db.employees.find(
        {"company_id": company_id, "status": "active"}, {"_id": 0}
    ).to_list(5000)

    # Mark last FPS of the year as final (if exists)
    last_payrun = await db.pay_runs.find_one(
        {"company_id": company_id},
        {"_id": 0},
        sort=[("pay_date", -1)],
    )
    if last_payrun:
        await db.pay_runs.update_one(
            {"payrun_id": last_payrun["payrun_id"]},
            {"$set": {"final_fps": True, "year_end_tax_year": tax_year}}
        )

    # Queue P60s
    p60_queue = []
    for emp in employees:
        rid = f"p60q_{uuid.uuid4().hex[:10]}"
        p60_queue.append(rid)
        await db.p60_queue.insert_one({
            "queue_id": rid,
            "employee_id": emp["employee_id"],
            "company_id": company_id,
            "tax_year": tax_year,
            "status": "queued",
            "created_at": now,
        })

    # EPS record
    from services.statutory_service import statutory_service
    eps = await statutory_service.get_eps_recovery_summary(company_id, 12, tax_year)
    eps_id = f"eps_{uuid.uuid4().hex[:12]}"
    await db.eps_submissions.insert_one({
        "submission_id": eps_id,
        "company_id": company_id,
        "tax_year": tax_year,
        "status": "draft",
        "totals": eps.get("recovery"),
        "created_by": user.user_id,
        "created_at": now,
    })

    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "action": "year_end_close",
        "entity_type": "tax_year",
        "entity_id": tax_year,
        "details": {"p60_count": len(p60_queue), "eps_id": eps_id},
        "timestamp": now,
    })

    return {
        "status": "closed",
        "tax_year": tax_year,
        "p60_queued": len(p60_queue),
        "eps_id": eps_id,
        "final_fps_marked": bool(last_payrun),
    }
