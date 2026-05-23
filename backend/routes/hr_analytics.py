"""
RealtouchHR - Compliance Calendar, HR Reports, Org Chart
Aggregates deadlines and produces analytical reports across all HR modules.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import os, sys, io, csv, jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(tags=["Reports & Calendar"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None

    class Config:
        extra = "ignore"


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


def _hr_only(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="HR/Admin only")


# =========================================================
#  COMPLIANCE CALENDAR — aggregates expiries & deadlines
# =========================================================

@router.get("/compliance-calendar")
async def compliance_calendar(days_ahead: int = 180, user: CurrentUser = Depends(get_current_user)):
    """
    Aggregates all upcoming compliance events from RTW, visa, training expiry, policy review,
    probation end, and pay-run deadlines.
    """
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=days_ahead)

    events: List[Dict[str, Any]] = []

    # 1. Employees: right-to-work expiry, visa expiry, probation end
    emps = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(length=5000)
    for e in emps:
        full_name = f"{e.get('first_name','')} {e.get('last_name','')}".strip()
        for field, label in (("visa_expiry_date", "Visa expiry"), ("rtw_expiry_date", "Right to Work expiry"), ("probation_end_date", "Probation end")):
            v = e.get(field)
            if v:
                try:
                    d = datetime.fromisoformat(str(v)).date()
                    if today <= d <= cutoff:
                        events.append({
                            "date": d.isoformat(), "category": "employee",
                            "title": f"{label} — {full_name}", "employee_id": e.get("employee_id"),
                            "severity": "high" if (d - today).days < 30 else "medium"
                        })
                except Exception:
                    pass

    # 2. RTW checks expiry
    rtws = await db.rtw_checks.find({"company_id": user.company_id, "expiry_date": {"$ne": None}}, {"_id": 0}).to_list(length=2000)
    for r in rtws:
        try:
            d = datetime.fromisoformat(str(r["expiry_date"])).date()
            if today <= d <= cutoff:
                events.append({
                    "date": d.isoformat(), "category": "rtw",
                    "title": f"RTW check follow-up — {r.get('employee_name', r.get('employee_id'))}",
                    "employee_id": r.get("employee_id"),
                    "severity": "high" if (d - today).days < 30 else "medium"
                })
        except Exception:
            pass

    # 3. Training records expiry
    trainings = await db.training_records.find({"company_id": user.company_id, "expiry_date": {"$ne": None}}, {"_id": 0}).to_list(length=5000)
    for t in trainings:
        try:
            d = datetime.fromisoformat(str(t["expiry_date"])).date()
            if today <= d <= cutoff:
                events.append({
                    "date": d.isoformat(), "category": "training",
                    "title": f"Training renewal — {t.get('course_title')}",
                    "employee_id": t.get("employee_id"),
                    "severity": "medium"
                })
        except Exception:
            pass

    # 4. Policy review dates
    policies = await db.policies.find({"company_id": user.company_id, "review_date": {"$ne": None}, "status": "active"}, {"_id": 0}).to_list(length=500)
    for p in policies:
        try:
            d = datetime.fromisoformat(str(p["review_date"])).date()
            if today <= d <= cutoff:
                events.append({
                    "date": d.isoformat(), "category": "policy",
                    "title": f"Policy review — {p.get('title')}",
                    "severity": "low"
                })
        except Exception:
            pass

    # 5. Sponsor licence renewal
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    if company and company.get("sponsor_licence_expiry"):
        try:
            d = datetime.fromisoformat(str(company["sponsor_licence_expiry"])).date()
            if today <= d <= cutoff:
                events.append({
                    "date": d.isoformat(), "category": "sponsor_licence",
                    "title": "UKVI Sponsor Licence renewal",
                    "severity": "high"
                })
        except Exception:
            pass

    events.sort(key=lambda x: x["date"])
    summary = {
        "high": sum(1 for e in events if e["severity"] == "high"),
        "medium": sum(1 for e in events if e["severity"] == "medium"),
        "low": sum(1 for e in events if e["severity"] == "low"),
        "total": len(events)
    }
    return {"today": today.isoformat(), "horizon": cutoff.isoformat(), "summary": summary, "events": events}


# =========================================================
#  HR REPORTS
# =========================================================

@router.get("/hr-reports/summary")
async def hr_reports_summary(user: CurrentUser = Depends(get_current_user)):
    """High-level HR analytics dashboard."""
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    today = datetime.now(timezone.utc).date()
    one_year_ago = today - timedelta(days=365)
    one_year_ago_iso = one_year_ago.isoformat()

    emps = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(length=5000)
    active = [e for e in emps if e.get("status", "active") == "active"]

    # Starters (joined in last 12 months)
    starters = []
    for e in emps:
        sd = e.get("start_date")
        if sd:
            try:
                d = datetime.fromisoformat(str(sd)).date()
                if d >= one_year_ago:
                    starters.append(e)
            except Exception:
                pass

    # Leavers (termination_date in last 12 months)
    leavers = []
    for e in emps:
        td = e.get("termination_date")
        if td:
            try:
                d = datetime.fromisoformat(str(td)).date()
                if d >= one_year_ago:
                    leavers.append(e)
            except Exception:
                pass

    # Turnover %
    avg_headcount = max(1, (len(active) + len(leavers)) / 2)
    turnover_pct = round(len(leavers) / avg_headcount * 100, 1)

    # Department breakdown
    dept_counts: Dict[str, int] = {}
    for e in active:
        d = e.get("department") or "Unassigned"
        dept_counts[d] = dept_counts.get(d, 0) + 1

    # Gender / ethnicity (if recorded)
    gender_counts: Dict[str, int] = {}
    for e in active:
        g = e.get("gender") or "Unknown"
        gender_counts[g] = gender_counts.get(g, 0) + 1

    # Absence (last 12 months)
    absences = await db.absence_records.find(
        {"company_id": user.company_id, "start_date": {"$gte": one_year_ago_iso}}, {"_id": 0}
    ).to_list(length=10000)
    total_absence_days = sum(a.get("duration_days", 1) for a in absences)
    avg_absence_per_emp = round(total_absence_days / max(1, len(active)), 1)

    # Training compliance
    courses = await db.training_courses.find({"company_id": user.company_id, "mandatory": True}, {"_id": 0}).to_list(length=200)
    mandatory_course_ids = [c["course_id"] for c in courses]
    training_records = await db.training_records.find(
        {"company_id": user.company_id, "course_id": {"$in": mandatory_course_ids}, "status": "completed"},
        {"_id": 0}
    ).to_list(length=10000)
    mandatory_requirements = len(active) * len(courses)
    completed_count = len(training_records)
    training_compliance_pct = round((completed_count / max(1, mandatory_requirements)) * 100, 1) if mandatory_requirements else 100.0

    return {
        "headcount": {"active": len(active), "total_on_record": len(emps)},
        "starters_last_12m": len(starters),
        "leavers_last_12m": len(leavers),
        "turnover_percent": turnover_pct,
        "department_breakdown": dept_counts,
        "gender_breakdown": gender_counts,
        "absence": {"total_days_12m": total_absence_days, "avg_days_per_employee": avg_absence_per_emp, "episodes_12m": len(absences)},
        "training_compliance_percent": training_compliance_pct,
        "training_required_total": mandatory_requirements,
        "training_completed_total": completed_count,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/hr-reports/headcount.csv")
async def headcount_csv(user: CurrentUser = Depends(get_current_user)):
    _hr_only(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    emps = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(length=10000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Employee ID", "First Name", "Last Name", "Email", "Department", "Job Title", "Start Date", "Status", "Employment Type"])
    for e in emps:
        w.writerow([e.get("employee_id"), e.get("first_name"), e.get("last_name"), e.get("email"),
                    e.get("department"), e.get("job_title"), e.get("start_date"),
                    e.get("status", "active"), e.get("employment_type")])
    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=headcount_{user.company_id}.csv"}
    )


# =========================================================
#  ORGANISATION CHART
# =========================================================

@router.get("/org-chart")
async def org_chart(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    emps = await db.employees.find(
        {"company_id": user.company_id, "status": {"$ne": "terminated"}},
        {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1,
         "job_title": 1, "department": 1, "line_manager_id": 1, "email": 1}
    ).to_list(length=5000)

    # Build a name lookup
    by_id = {e["employee_id"]: e for e in emps}

    # Find roots (no line_manager or line_manager not in set)
    roots = []
    children: Dict[str, List[Dict[str, Any]]] = {}
    for e in emps:
        lm = e.get("line_manager_id")
        if not lm or lm not in by_id:
            roots.append(e["employee_id"])
        else:
            children.setdefault(lm, []).append(e)

    def build_node(emp_id: str) -> Dict[str, Any]:
        e = by_id[emp_id]
        return {
            "employee_id": emp_id,
            "name": f"{e.get('first_name','')} {e.get('last_name','')}".strip(),
            "title": e.get("job_title"),
            "department": e.get("department"),
            "email": e.get("email"),
            "reports": [build_node(c["employee_id"]) for c in children.get(emp_id, [])]
        }

    tree = [build_node(r) for r in roots]
    # Stats
    total_managers = sum(1 for eid in by_id if eid in children)
    return {
        "tree": tree,
        "stats": {
            "total_employees": len(emps),
            "total_managers": total_managers,
            "max_depth": _max_depth(tree)
        }
    }


def _max_depth(nodes: List[Dict[str, Any]], current: int = 1) -> int:
    if not nodes:
        return current - 1
    return max((_max_depth(n.get("reports", []), current + 1) for n in nodes), default=current)
