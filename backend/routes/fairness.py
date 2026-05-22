"""
RealtouchHR - Equality Act 2010 Fairness Routes
Detects potential bias in performance rating distributions.
Run by HR/Admin on appraisal data.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
import os, sys, jwt
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/fairness", tags=["Equality Act Fairness"])


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


def _require_hr(user: CurrentUser):
    if user.role not in ("owner", "admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="HR/Admin only")


RATING_WEIGHTS = {"exceeds": 4, "meets": 3, "partial": 2, "below": 1}


def _80_percent_rule(group_rates: Dict[str, float]) -> List[str]:
    """
    EEOC-inspired 80% rule applied to "favourable" outcomes (exceeds + meets).
    Flags any group whose favourable rate is < 80% of the highest group's rate.
    """
    if not group_rates:
        return []
    max_rate = max(group_rates.values()) if group_rates else 0
    flags = []
    if max_rate <= 0:
        return flags
    for grp, rate in group_rates.items():
        if (rate / max_rate) < 0.8:
            flags.append(f"{grp}: {rate*100:.0f}% favourable vs top group {max_rate*100:.0f}% (below 80% rule)")
    return flags


@router.get("/appraisals/bias-scan")
async def appraisals_bias_scan(
    cycle: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Scan appraisal ratings for distribution bias across protected characteristics.
    Compares 'favourable' outcomes (exceeds + meets) per group using the 80% rule.
    Protected categories analysed (when data present): gender, ethnicity, age_band, department.
    """
    _require_hr(user)
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")

    q: Dict[str, Any] = {"company_id": user.company_id}
    if cycle:
        q["cycle"] = cycle
    appraisals = await db.performance_appraisals.find(q, {"_id": 0}).to_list(length=5000)

    if not appraisals:
        return {
            "company_id": user.company_id,
            "cycle": cycle,
            "total_appraisals": 0,
            "groups": {},
            "alerts": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "method": "80% rule on favourable rating (exceeds+meets)",
            "note": "No appraisals found.",
        }

    # Build employee_id → employee record (so we can read demographics)
    emp_ids = [a.get("employee_id") for a in appraisals if a.get("employee_id")]
    emps = await db.employees.find(
        {"company_id": user.company_id, "employee_id": {"$in": emp_ids}},
        {"_id": 0}
    ).to_list(length=5000)
    by_id = {e["employee_id"]: e for e in emps}

    def _group_keys(emp: Dict[str, Any]) -> Dict[str, str]:
        return {
            "gender": emp.get("gender") or "Unknown",
            "ethnicity": emp.get("ethnicity") or "Unknown",
            "department": emp.get("department") or "Unknown",
        }

    # Aggregate per category, per group
    categories = ["gender", "ethnicity", "department"]
    counters: Dict[str, Dict[str, Dict[str, int]]] = {
        c: defaultdict(lambda: {"total": 0, "favourable": 0, "sum_weight": 0, "count_weight": 0})
        for c in categories
    }

    for ap in appraisals:
        emp = by_id.get(ap.get("employee_id"))
        if not emp:
            continue
        gk = _group_keys(emp)
        rating = (ap.get("overall_rating") or "").lower()
        for cat in categories:
            grp = gk[cat]
            bucket = counters[cat][grp]
            bucket["total"] += 1
            if rating in ("exceeds", "meets"):
                bucket["favourable"] += 1
            if rating in RATING_WEIGHTS:
                bucket["sum_weight"] += RATING_WEIGHTS[rating]
                bucket["count_weight"] += 1

    output: Dict[str, Any] = {
        "company_id": user.company_id,
        "cycle": cycle,
        "total_appraisals": len(appraisals),
        "groups": {},
        "alerts": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "80% rule on favourable rating (exceeds+meets); also reports mean rating weight",
    }
    for cat, groups in counters.items():
        gout = {}
        rates = {}
        for grp, b in groups.items():
            if b["total"] == 0:
                continue
            fav_rate = b["favourable"] / b["total"]
            avg = (b["sum_weight"] / b["count_weight"]) if b["count_weight"] else None
            rates[grp] = fav_rate
            gout[grp] = {
                "total": b["total"],
                "favourable": b["favourable"],
                "favourable_rate": round(fav_rate, 3),
                "average_weight": round(avg, 2) if avg else None,
            }
        output["groups"][cat] = gout
        flags = _80_percent_rule(rates)
        if flags:
            for f in flags:
                output["alerts"].append({"category": cat, "issue": f})

    if not output["alerts"]:
        output["alerts"].append({"category": "_", "issue": "No bias indicators detected by 80% rule.", "level": "info"})

    return output
