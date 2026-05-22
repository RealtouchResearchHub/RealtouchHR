"""
RealtouchHR - GDPR / Data Protection Service
Self-service data export (Article 15) and right to erasure (Article 17)
"""
import os
import sys
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

logger = logging.getLogger(__name__)


# Collections that may hold personal data tied to a user/employee
PERSONAL_DATA_COLLECTIONS = [
    "users",
    "employees",
    "leave_requests",
    "documents",
    "shifts",
    "timesheets",
    "payslips",
    "pay_runs",
    "notifications",
    "audit_log",
    "rtw_checks",
    "cos_register",
    "pension_enrolments",
    "statutory_payments",
    "performance_objectives",
    "performance_appraisals",
    "performance_notes",
    "employee_cases",
    "secure_documents",
    "user_sessions",
    "user_2fa",
    "payment_transactions",
    "download_passes",
    "tax_documents",
    "p11d_records",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Strip Mongo internals + sensitive fields before exporting."""
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if k in ("password_hash", "totp_secret", "totp_backup_codes"):
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def build_user_export(user_id: str, email: str, company_id: Optional[str], employee_id: Optional[str]) -> Dict[str, Any]:
    """
    Returns a complete export bundle for a user (UK GDPR Article 15).
    Includes user profile, employee record (if any), payslips, leave, documents, audit history.
    """
    bundle: Dict[str, Any] = {
        "export_id": f"gdpr_export_{uuid.uuid4().hex[:12]}",
        "generated_at": _now(),
        "subject": {"user_id": user_id, "email": email, "company_id": company_id, "employee_id": employee_id},
        "data": {},
        "notes": [
            "This export contains all personal data held about you across the RealtouchHR platform.",
            "Sensitive credentials (password hashes, 2FA secrets) are intentionally excluded.",
            "Retention: certain records (payroll, audit) are retained for 6-7 years per HMRC and UK Data Protection Act 2018.",
        ],
    }

    # User profile
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0, "totp_secret": 0, "totp_backup_codes": 0})
    if user_doc:
        bundle["data"]["user_profile"] = _clean(user_doc)

    # Employee record (if linked)
    if employee_id:
        emp_doc = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
        if emp_doc:
            bundle["data"]["employee_record"] = _clean(emp_doc)
    # Also try email match
    emp_docs = await db.employees.find({"email": email}, {"_id": 0}).to_list(length=10)
    if emp_docs:
        bundle["data"]["employee_records_by_email"] = [_clean(d) for d in emp_docs]

    # Per-collection scan by user_id / employee_id / email
    queries: Dict[str, Dict[str, Any]] = {
        "leave_requests": {"$or": [{"employee_id": employee_id}, {"approved_by": user_id}]},
        "documents": {"$or": [{"employee_id": employee_id}, {"created_by": user_id}]},
        "shifts": {"employee_id": employee_id} if employee_id else None,
        "timesheets": {"employee_id": employee_id} if employee_id else None,
        "payslips": {"employee_id": employee_id} if employee_id else None,
        "notifications": {"user_id": user_id},
        "audit_log": {"user_id": user_id},
        "rtw_checks": {"employee_id": employee_id} if employee_id else None,
        "cos_register": {"employee_id": employee_id} if employee_id else None,
        "pension_enrolments": {"employee_id": employee_id} if employee_id else None,
        "statutory_payments": {"employee_id": employee_id} if employee_id else None,
        "performance_objectives": {"employee_id": employee_id} if employee_id else None,
        "performance_appraisals": {"employee_id": employee_id} if employee_id else None,
        "performance_notes": {"employee_id": employee_id} if employee_id else None,
        "employee_cases": {"$or": [{"employee_id": employee_id}, {"raised_by": user_id}]} if employee_id else None,
        "payment_transactions": {"user_id": user_id},
        "download_passes": {"user_id": user_id},
        "p11d_records": {"employee_id": employee_id} if employee_id else None,
        "user_sessions": {"user_id": user_id},
    }

    for coll_name, query in queries.items():
        if not query:
            continue
        # Strip None-keyed $or values
        if "$or" in query:
            query["$or"] = [c for c in query["$or"] if list(c.values())[0]]
            if not query["$or"]:
                continue
        try:
            docs = await db[coll_name].find(query, {"_id": 0}).to_list(length=1000)
            if docs:
                bundle["data"][coll_name] = [_clean(d) for d in docs]
        except Exception as exc:
            logger.warning(f"GDPR export: skipping {coll_name}: {exc}")

    bundle["summary"] = {
        "total_categories": len(bundle["data"]),
        "categories": list(bundle["data"].keys()),
    }
    return bundle


async def create_erasure_request(user_id: str, company_id: str, requester_email: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Employee/user submits a 'right to be forgotten' request. HR/Admin must process it."""
    req = {
        "request_id": f"erasure_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "company_id": company_id,
        "requester_email": requester_email,
        "reason": reason,
        "status": "pending",
        "created_at": _now(),
        "processed_at": None,
        "processed_by": None,
        "outcome": None,
    }
    await db.gdpr_erasure_requests.insert_one(dict(req))
    return req


async def list_erasure_requests(company_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"company_id": company_id}
    if status:
        q["status"] = status
    docs = await db.gdpr_erasure_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(length=500)
    return docs


async def process_erasure_request(request_id: str, company_id: str, processor_user_id: str, processor_name: str, action: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    action: 'approve_anonymize' | 'approve_delete' | 'reject'
    On approval, anonymizes PII fields across personal data collections while preserving payroll history (legal retention).
    """
    req = await db.gdpr_erasure_requests.find_one({"request_id": request_id, "company_id": company_id}, {"_id": 0})
    if not req:
        return {"ok": False, "error": "Request not found"}
    if req["status"] != "pending":
        return {"ok": False, "error": f"Request already {req['status']}"}

    outcome = {"action": action, "anonymized": [], "deleted": []}
    if action == "reject":
        await db.gdpr_erasure_requests.update_one(
            {"request_id": request_id},
            {"$set": {"status": "rejected", "processed_at": _now(), "processed_by": processor_user_id, "outcome": outcome, "notes": notes}}
        )
        return {"ok": True, "status": "rejected"}

    target_user_id = req["user_id"]
    # Find linked employee record(s)
    user_doc = await db.users.find_one({"user_id": target_user_id}, {"_id": 0})
    if not user_doc:
        return {"ok": False, "error": "Target user not found"}

    employee_id = user_doc.get("employee_id")
    employee_docs = await db.employees.find({"email": user_doc.get("email")}, {"_id": 0}).to_list(length=10)
    employee_ids = [e["employee_id"] for e in employee_docs]
    if employee_id and employee_id not in employee_ids:
        employee_ids.append(employee_id)

    anon_marker = f"ERASED_{uuid.uuid4().hex[:8]}"

    if action == "approve_anonymize":
        # Anonymise PII in users
        await db.users.update_one(
            {"user_id": target_user_id},
            {"$set": {
                "name": "Erased User",
                "email": f"{anon_marker}@erased.local",
                "picture": None,
                "is_erased": True,
                "erased_at": _now(),
            },
             "$unset": {"password_hash": "", "totp_secret": "", "totp_backup_codes": "", "totp_enabled": ""}}
        )
        outcome["anonymized"].append("users")

        # Anonymise employee records (preserve payroll IDs but mask PII)
        for emp_id in employee_ids:
            await db.employees.update_one(
                {"employee_id": emp_id},
                {"$set": {
                    "first_name": "Erased",
                    "last_name": "User",
                    "email": f"{anon_marker}@erased.local",
                    "ni_number": "QQ999999Q",
                    "bank_account": None,
                    "bank_sort_code": None,
                    "immigration_status": None,
                    "is_erased": True,
                    "erased_at": _now(),
                }}
            )
            outcome["anonymized"].append(f"employee:{emp_id}")

        # Drop sessions (force logout)
        del_sessions = await db.user_sessions.delete_many({"user_id": target_user_id})
        outcome["deleted"].append(f"user_sessions:{del_sessions.deleted_count}")

        # Delete notifications (not legally required)
        del_n = await db.notifications.delete_many({"user_id": target_user_id})
        outcome["deleted"].append(f"notifications:{del_n.deleted_count}")

        # Document storage cleanup (remove secure docs, performance notes)
        if employee_ids:
            del_pn = await db.performance_notes.delete_many({"employee_id": {"$in": employee_ids}})
            outcome["deleted"].append(f"performance_notes:{del_pn.deleted_count}")

        status = "completed_anonymized"
    elif action == "approve_delete":
        # Full delete — only safe when no payroll history exists (HMRC retention rules)
        payslip_exists = await db.payslips.find_one({"employee_id": {"$in": employee_ids}}) if employee_ids else None
        payrun_exists = await db.pay_runs.find_one({"company_id": company_id, "payslips.employee_id": {"$in": employee_ids}}) if employee_ids else None
        if payslip_exists or payrun_exists:
            return {"ok": False, "error": "Cannot fully delete — payroll history exists (HMRC 6-year retention). Use approve_anonymize instead."}

        del_u = await db.users.delete_one({"user_id": target_user_id})
        outcome["deleted"].append(f"users:{del_u.deleted_count}")
        if employee_ids:
            del_e = await db.employees.delete_many({"employee_id": {"$in": employee_ids}})
            outcome["deleted"].append(f"employees:{del_e.deleted_count}")
        del_s = await db.user_sessions.delete_many({"user_id": target_user_id})
        outcome["deleted"].append(f"user_sessions:{del_s.deleted_count}")
        del_n = await db.notifications.delete_many({"user_id": target_user_id})
        outcome["deleted"].append(f"notifications:{del_n.deleted_count}")
        status = "completed_deleted"
    else:
        return {"ok": False, "error": f"Unknown action: {action}"}

    await db.gdpr_erasure_requests.update_one(
        {"request_id": request_id},
        {"$set": {
            "status": status,
            "processed_at": _now(),
            "processed_by": processor_user_id,
            "processor_name": processor_name,
            "outcome": outcome,
            "notes": notes,
        }}
    )

    # Audit
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": processor_user_id,
        "user_name": processor_name,
        "action": "gdpr.erasure_processed",
        "entity_type": "erasure_request",
        "entity_id": request_id,
        "details": {"target_user_id": target_user_id, "action": action, "outcome": outcome},
        "timestamp": _now(),
    })

    return {"ok": True, "status": status, "outcome": outcome}


async def list_company_personal_data_overview(company_id: str) -> Dict[str, Any]:
    """
    HR/Admin view: how much personal data we hold across collections for this company.
    """
    overview: Dict[str, Any] = {"company_id": company_id, "generated_at": _now(), "counts": {}}
    counts_queries = {
        "users": {"company_id": company_id},
        "employees": {"company_id": company_id},
        "leave_requests": {"company_id": company_id},
        "documents": {"company_id": company_id},
        "audit_log": {"company_id": company_id},
        "notifications": {"company_id": company_id},
        "performance_appraisals": {"company_id": company_id},
        "employee_cases": {"company_id": company_id},
        "secure_documents": {"company_id": company_id},
        "rtw_checks": {"company_id": company_id},
        "cos_register": {"company_id": company_id},
        "p11d_records": {"company_id": company_id},
    }
    for coll, q in counts_queries.items():
        try:
            overview["counts"][coll] = await db[coll].count_documents(q)
        except Exception:
            overview["counts"][coll] = 0

    # Retention info
    overview["retention_policy"] = {
        "audit_log": "7 years (UK Data Protection Act 2018, HMRC RTI)",
        "payslips": "6 years (HMRC PAYE)",
        "p11d_records": "6 years (HMRC P11D)",
        "rti_submissions": "6 years",
        "leave_requests": "3 years (statutory minimum)",
        "ukvi_alerts": "5 years (UKVI Sponsor Licence duties)",
        "tax_documents": "6 years",
    }
    return overview
