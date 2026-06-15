"""
RealtouchHR - UKVI Compliance Routes
UK Visas and Immigration Sponsor Compliance API

IMPORTANT DISCLAIMER:
This module assists with UKVI compliance record-keeping but does NOT replace
legal advice. Sponsor compliance is the employer's legal responsibility.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ukvi", tags=["UKVI Compliance"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


def _normalize_user_doc(user_doc: dict) -> dict:
    normalized = dict(user_doc)
    email = (normalized.get("email") or "").strip()
    normalized["name"] = (normalized.get("name") or email.split("@")[0] or "User").strip()
    return normalized


class ImmigrationStatusUpdate(BaseModel):
    visa_type: Optional[str] = None
    visa_start_date: Optional[str] = None
    visa_end_date: Optional[str] = None
    cos_reference: Optional[str] = None  # Certificate of Sponsorship
    soc_code: Optional[str] = None  # Standard Occupational Classification
    right_to_work_expiry: Optional[str] = None
    right_to_work_check_date: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    share_code: Optional[str] = None
    biometric_residence_permit: Optional[str] = None
    nationality: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    resolution_note: str = Field(..., min_length=10)


class MarkReportedRequest(BaseModel):
    sms_reference: str = Field(..., description="Reference from Sponsor Management System")


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: open | in_progress | dismissed | false_positive")
    note: Optional[str] = None


# ==================== AUTH HELPERS ====================

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
            return User(**_normalize_user_doc(user_doc))
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**_normalize_user_doc(user_doc))


async def require_hr_admin(request: Request) -> User:
    """Require HR admin or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "hr_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only HR Admin or Owner can manage UKVI compliance"
        )
    return user


# ==================== DASHBOARD ====================

@router.get("/dashboard")
async def get_ukvi_dashboard(user: User = Depends(require_hr_admin)):
    """
    Get UKVI compliance dashboard for the company.
    
    Returns:
    - Overall compliance score
    - Employee status breakdown
    - Active alerts
    - Pending reportable events
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.ukvi_service import ukvi_service
    
    try:
        dashboard = await ukvi_service.get_company_ukvi_dashboard(user.company_id)
        return {
            **dashboard,
            "disclaimer": "This dashboard assists with UKVI compliance but does not constitute legal advice."
        }
    except Exception as e:
        logger.error(f"UKVI dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EMPLOYEE COMPLIANCE ====================

@router.get("/employees/{employee_id}/compliance")
async def get_employee_ukvi_compliance(
    employee_id: str,
    user: User = Depends(require_hr_admin)
):
    """
    Get UKVI compliance score and status for an employee.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Verify employee belongs to company
    employee = await db.employees.find_one(
        {"employee_id": employee_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    from services.ukvi_service import ukvi_service
    
    try:
        compliance = await ukvi_service.calculate_employee_compliance_score(
            employee_id,
            user.company_id
        )
        return compliance
    except Exception as e:
        logger.error(f"Employee compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/employees/{employee_id}/immigration")
async def update_employee_immigration(
    employee_id: str,
    update: ImmigrationStatusUpdate,
    user: User = Depends(require_hr_admin)
):
    """
    Update employee immigration/visa status.
    
    Automatically detects and flags reportable changes.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get current employee data
    employee = await db.employees.find_one(
        {"employee_id": employee_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    old_immigration = employee.get("immigration_status", {})
    
    # Build updated immigration data
    new_immigration = {**old_immigration}
    update_dict = update.dict(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            new_immigration[key] = value
    
    now = datetime.now(timezone.utc)
    
    # Update employee record
    await db.employees.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "immigration_status": new_immigration,
            "updated_at": now.isoformat()
        }}
    )
    
    # Detect reportable changes
    from services.ukvi_service import ukvi_service
    
    events = await ukvi_service.detect_reportable_changes(
        employee_id,
        user.company_id,
        old_immigration,
        new_immigration
    )
    
    # Log audit entry
    await db.audit_log.insert_one({
        "action": "immigration_update",
        "entity_type": "employee",
        "entity_id": employee_id,
        "company_id": user.company_id,
        "performed_by": user.user_id,
        "changes": update_dict,
        "reportable_events_detected": len(events),
        "timestamp": now.isoformat()
    })
    
    return {
        "status": "updated",
        "employee_id": employee_id,
        "immigration_status": new_immigration,
        "reportable_events_detected": len(events),
        "events": [e.to_dict() for e in events] if events else []
    }


# ==================== ALERTS ====================

@router.get("/alerts")
async def list_ukvi_alerts(
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(require_hr_admin)
):
    """
    List UKVI compliance alerts.
    
    Filter by resolved status and severity (low, medium, high, critical).
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    query = {"company_id": user.company_id}
    if resolved is not None:
        query["status"] = "resolved" if resolved else "open"
    if severity:
        query["severity"] = severity
    
    alerts = await db.ukvi_alerts.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "alerts": alerts,
        "total": len(alerts)
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_ukvi_alert(
    alert_id: str,
    resolve_request: ResolveAlertRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Resolve a UKVI compliance alert.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Verify alert belongs to company
    alert = await db.ukvi_alerts.find_one(
        {"alert_id": alert_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    from services.ukvi_service import ukvi_service
    
    try:
        result = await ukvi_service.resolve_alert(
            alert_id,
            user.user_id,
            resolve_request.resolution_note
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/alerts/generate")
async def generate_alerts(user: User = Depends(require_hr_admin)):
    """
    Manually trigger alert generation for expiring documents.
    
    This is normally run as a scheduled daily task.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.ukvi_service import ukvi_service
    
    try:
        alerts = await ukvi_service.generate_expiry_alerts(user.company_id)
        return {
            "status": "completed",
            "alerts_generated": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
    except Exception as e:
        logger.error(f"Alert generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REPORTING ====================

@router.get("/reporting/checklist")
async def get_reporting_checklist(user: User = Depends(require_hr_admin)):
    """
    Get checklist of pending UKVI reports.
    
    Events must be reported within 10 working days.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.ukvi_service import ukvi_service
    
    try:
        checklist = await ukvi_service.get_reporting_checklist(user.company_id)
        return {
            **checklist,
            "disclaimer": "Reports must be submitted to UKVI via the Sponsor Management System within 10 working days."
        }
    except Exception as e:
        logger.error(f"Reporting checklist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reporting/events")
async def list_reporting_events(
    reported: Optional[bool] = None,
    limit: int = 50,
    user: User = Depends(require_hr_admin)
):
    """
    List UKVI reportable events.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    query = {"company_id": user.company_id}
    if reported is not None:
        query["submitted"] = reported
    
    events = await db.ukvi_reporting_events.find(
        query,
        {"_id": 0}
    ).sort("event_date", -1).limit(limit).to_list(limit)
    
    return {
        "events": events,
        "total": len(events)
    }


@router.post("/reporting/events/{event_id}/mark-reported")
async def mark_event_reported(
    event_id: str,
    mark_request: MarkReportedRequest,
    user: User = Depends(require_hr_admin)
):
    """
    Mark a reportable event as reported to UKVI.
    
    Include the SMS reference number from the Sponsor Management System.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Verify event belongs to company
    event = await db.ukvi_reporting_events.find_one(
        {"event_id": event_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    from services.ukvi_service import ukvi_service
    
    try:
        result = await ukvi_service.mark_event_reported(
            event_id,
            mark_request.sms_reference,
            user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== VISA TYPES REFERENCE ====================

@router.get("/visa-types")
async def list_visa_types(user: User = Depends(get_current_user)):
    """
    Get list of supported UK visa types.
    """
    from services.ukvi_service import VisaType

    return {
        "visa_types": [
            {"code": VisaType.SKILLED_WORKER.value, "name": "Skilled Worker", "sponsored": True},
            {"code": VisaType.INTRA_COMPANY_TRANSFER.value, "name": "Intra-company Transfer", "sponsored": True},
            {"code": VisaType.GLOBAL_TALENT.value, "name": "Global Talent", "sponsored": False},
            {"code": VisaType.INNOVATOR_FOUNDER.value, "name": "Innovator Founder", "sponsored": True},
            {"code": VisaType.GRADUATE.value, "name": "Graduate", "sponsored": False},
            {"code": VisaType.SCALE_UP.value, "name": "Scale-up", "sponsored": True},
            {"code": VisaType.HEALTH_CARE.value, "name": "Health & Care Worker", "sponsored": True},
            {"code": VisaType.SEASONAL_WORKER.value, "name": "Seasonal Worker", "sponsored": True},
            {"code": VisaType.BRITISH_CITIZEN.value, "name": "British Citizen", "sponsored": False},
            {"code": VisaType.SETTLED.value, "name": "Settled Status (ILR)", "sponsored": False},
            {"code": VisaType.OTHER.value, "name": "Other", "sponsored": False}
        ]
    }


# ===========================================================================
# UKVI COMPLIANCE SCANNER — Premium feature (2 scans/billing month, all plans)
# ===========================================================================

@router.get("/compliance/status")
async def get_compliance_scanner_status(user: User = Depends(require_hr_admin)):
    """
    Get compliance scanner quota status and recent scan history for this company.
    Included in all subscription plans (2 scans per billing month).
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    from services.ukvi_compliance_service import ukvi_compliance_service

    quota = await ukvi_compliance_service.get_scan_quota(user.company_id, db)

    _all_scans = await db.ukvi_compliance_scans.find(
        {"company_id": user.company_id},
        {"_id": 0},
    ).to_list(1000)
    recent_scans = sorted(_all_scans, key=lambda x: x.get("created_at", ""), reverse=True)[:10]

    return {
        "quota": quota,
        "recent_scans": recent_scans,
        "disclaimer": (
            "This scanner assists with internal UKVI compliance record-keeping. "
            "It does not constitute legal advice. Sponsor compliance is the employer's legal responsibility."
        ),
    }


@router.post("/compliance/scans/run")
async def run_compliance_scan(user: User = Depends(require_hr_admin)):
    """
    Trigger a full UKVI compliance scan for this company.
    Deducts one scan from the monthly quota (2 per billing month, all plans).
    Returns scan_id immediately; use GET /compliance/scans/{scan_id}/preview for results.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="Company not found")
    # Allow owners, trial companies, and any paid plan to run scans
    sub_status = company.get("subscription_status") or company.get("subscription_plan", "free")
    is_trial = company.get("trial_active") or company.get("trial_ends_at")
    if sub_status in ("free", "inactive") and not company.get("subscription_active") and not is_trial and user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=402,
            detail="A paid subscription is required to run UKVI compliance scans."
        )

    from services.ukvi_compliance_service import ukvi_compliance_service

    try:
        result = await ukvi_compliance_service.run_scan(
            company_id=user.company_id,
            initiated_by=user.user_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        logger.error(f"UKVI scan error: {exc}")
        raise HTTPException(status_code=500, detail="Scan failed — please try again.")

    # Audit log
    await db.audit_log.insert_one({
        "audit_id": f"aud_{__import__('uuid').uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "action": "ukvi_compliance_scan_run",
        "entity_type": "ukvi_scan",
        "entity_id": result["scan_id"],
        "details": {"score": result["overall_score"], "risk_level": result["risk_level"]},
        "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    })

    return result


@router.get("/compliance/scans/{scan_id}/preview")
async def get_scan_preview(scan_id: str, user: User = Depends(require_hr_admin)):
    """
    Get structured compliance scan results (free preview — no additional charge).
    Returns per-employee and per-category breakdowns.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    from services.ukvi_compliance_service import ukvi_compliance_service

    try:
        preview = await ukvi_compliance_service.get_scan_preview(scan_id, user.company_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return preview


@router.post("/compliance/scans/{scan_id}/export")
async def export_scan_report(
    scan_id: str,
    format: str = "pdf",
    user: User = Depends(require_hr_admin),
):
    """
    Export a compliance scan as PDF or DOCX.
    Requires ukvi_report_download feature entitlement (Professional/Enterprise plans).
    Format: ?format=pdf (default) or ?format=docx
    """
    from fastapi.responses import StreamingResponse
    import io as _io

    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    if format not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'docx'")

    # Check plan entitlement — all paid plans (starter, professional, enterprise) can download reports
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0}) or {}
    plan = (company.get("subscription_plan") or "free").lower()
    if plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(
            status_code=402,
            detail="UKVI compliance report downloads require an active subscription (Starter, Professional or Enterprise)."
        )

    company_name = company.get("name", "Your Company")

    from services.ukvi_compliance_service import ukvi_compliance_service

    try:
        if format == "pdf":
            data = await ukvi_compliance_service.generate_pdf_report(scan_id, user.company_id, company_name, db)
            media_type = "application/pdf"
            filename = f"ukvi_compliance_{scan_id[:8]}.pdf"
        else:
            data = await ukvi_compliance_service.generate_docx_report(scan_id, user.company_id, company_name, db)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"ukvi_compliance_{scan_id[:8]}.docx"
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"UKVI report export error: {exc}")
        raise HTTPException(status_code=500, detail="Report generation failed.")

    # Record export
    await db.ukvi_report_exports.insert_one({
        "export_id": f"exp_{__import__('uuid').uuid4().hex[:12]}",
        "scan_id": scan_id,
        "company_id": user.company_id,
        "format": format,
        "generated_by": user.user_id,
        "file_size": len(data),
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    })

    await db.audit_log.insert_one({
        "audit_id": f"aud_{__import__('uuid').uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "action": "ukvi_report_exported",
        "entity_type": "ukvi_scan",
        "entity_id": scan_id,
        "details": {"format": format},
        "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    })

    return StreamingResponse(
        _io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/compliance/alerts/{alert_id}")
async def update_alert_status(
    alert_id: str,
    body: AlertStatusUpdate,
    user: User = Depends(require_hr_admin),
):
    """Update an alert's status (in_progress, dismissed, false_positive, open)."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    allowed = {"open", "in_progress", "dismissed", "false_positive"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(allowed)}")

    alert = await db.ukvi_compliance_alerts.find_one(
        {"alert_id": alert_id, "company_id": user.company_id}, {"_id": 0}
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    updates = {"status": body.status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.note:
        updates["note"] = body.note
    await db.ukvi_compliance_alerts.update_one({"alert_id": alert_id}, {"$set": updates})
    return {"alert_id": alert_id, "status": body.status}


@router.get("/compliance/rules")
async def list_compliance_rules(user: User = Depends(require_hr_admin)):
    """Return all compliance rules in the engine."""
    from services.ukvi_compliance_service import COMPLIANCE_RULES
    return {"rules": COMPLIANCE_RULES, "total": len(COMPLIANCE_RULES)}


@router.get("/compliance/scans")
async def list_compliance_scans(
    limit: int = 20,
    user: User = Depends(require_hr_admin),
):
    """List all compliance scans for this company (most recent first)."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    scans = await db.ukvi_compliance_scans.find(
        {"company_id": user.company_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    ).limit(limit).to_list(limit)

    return {"scans": scans, "total": len(scans)}
