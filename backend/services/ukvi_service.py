"""
RealtouchHR - UKVI Compliance Service
UK Visas and Immigration Sponsor Compliance Management

For companies with a Sponsor Licence to employ migrant workers on work visas.

KEY COMPLIANCE REQUIREMENTS:
1. Record-keeping duties (Appendix D records)
2. Reporting duties (10-day reporting for certain changes)
3. Migrant tracking (start date, end date, right to work)
4. Sponsor Management System (SMS) integration readiness

IMPORTANT DISCLAIMER:
This module assists with UKVI compliance record-keeping but does NOT replace
legal advice. Sponsor compliance is the employer's legal responsibility.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid
import hashlib

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

logger = logging.getLogger(__name__)


# ==================== ENUMS AND CONSTANTS ====================

class UKVIReportingEvent(str, Enum):
    """Events that must be reported to UKVI within 10 working days"""
    ABSENCE_STARTED = "absence_started"
    ABSENCE_EXCEEDS_10_DAYS = "absence_exceeds_10_days"
    CONTRACT_ENDED = "contract_ended"
    SALARY_CHANGE = "salary_change"
    ROLE_CHANGE = "role_change"
    LOCATION_CHANGE = "location_change"
    CONTACT_CHANGE = "contact_change"
    RESIGNATION = "resignation"
    DISMISSAL = "dismissal"
    NOT_STARTING = "not_starting"
    SPONSOR_WITHDRAWAL = "sponsor_withdrawal"


class VisaType(str, Enum):
    """Common UK work visa types"""
    SKILLED_WORKER = "skilled_worker"
    INTRA_COMPANY_TRANSFER = "intra_company_transfer"
    GLOBAL_TALENT = "global_talent"
    INNOVATOR_FOUNDER = "innovator_founder"
    GRADUATE = "graduate"
    SCALE_UP = "scale_up"
    HEALTH_CARE = "health_care"
    SEASONAL_WORKER = "seasonal_worker"
    BRITISH_CITIZEN = "british_citizen"
    SETTLED = "settled"  # ILR/Pre-settled/Settled status
    OTHER = "other"


class ComplianceStatus(str, Enum):
    """Employee UKVI compliance status"""
    COMPLIANT = "compliant"
    ACTION_REQUIRED = "action_required"
    URGENT = "urgent"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"


# Appendix D record categories
APPENDIX_D_CATEGORIES = {
    "employment_records": [
        "job_title", "salary", "start_date", "work_location",
        "absence_records", "disciplinary_records"
    ],
    "personal_information": [
        "name", "date_of_birth", "gender", "nationality",
        "passport_number", "passport_expiry", "uk_address",
        "contact_number", "email"
    ],
    "right_to_work": [
        "right_to_work_check_date", "right_to_work_document_type",
        "right_to_work_expiry", "share_code", "biometric_residence_permit"
    ],
    "visa_information": [
        "visa_type", "cos_reference", "visa_start_date", "visa_end_date",
        "soc_code", "visa_conditions"
    ]
}


# ==================== DATA CLASSES ====================

@dataclass
class UKVIAlert:
    """Alert for UKVI compliance action required"""
    alert_id: str
    employee_id: str
    company_id: str
    alert_type: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    action_required: str
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "action_required": self.action_required,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by
        }


@dataclass
class ReportingEvent:
    """UKVI reportable event"""
    event_id: str
    employee_id: str
    company_id: str
    event_type: UKVIReportingEvent
    event_date: datetime
    details: Dict[str, Any]
    reported: bool = False
    reported_date: Optional[datetime] = None
    sms_reference: Optional[str] = None  # Reference from Sponsor Management System
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "event_type": self.event_type.value if isinstance(self.event_type, UKVIReportingEvent) else self.event_type,
            "event_date": self.event_date.isoformat(),
            "details": self.details,
            "reported": self.reported,
            "reported_date": self.reported_date.isoformat() if self.reported_date else None,
            "sms_reference": self.sms_reference,
            "created_at": self.created_at.isoformat()
        }


# ==================== UKVI SERVICE ====================

class UKVIComplianceService:
    """
    Service for managing UKVI sponsor compliance.
    
    Key responsibilities:
    - Track employee visa/immigration status
    - Generate alerts for expiring documents
    - Detect and flag reportable events
    - Maintain Appendix D compliant records
    - Calculate compliance scores
    """
    
    def __init__(self):
        # Configurable warning periods (days before expiry)
        self.visa_expiry_warning_days = [90, 60, 30, 14, 7]
        self.rtw_check_warning_days = [30, 14, 7, 1]
        self.passport_expiry_warning_days = [180, 90, 30]
    
    # ==================== COMPLIANCE SCORING ====================
    
    async def calculate_employee_compliance_score(
        self,
        employee_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Calculate UKVI compliance score for an employee.
        
        Returns score 0-100 with breakdown of issues.
        """
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        immigration = employee.get("immigration_status", {})
        
        # Check if UKVI compliance applies
        visa_type = immigration.get("visa_type", "")
        if visa_type in ["british_citizen", VisaType.BRITISH_CITIZEN.value]:
            return {
                "employee_id": employee_id,
                "score": 100,
                "status": ComplianceStatus.NOT_APPLICABLE.value,
                "message": "British citizen - no UKVI compliance required",
                "issues": []
            }
        
        score = 100
        issues = []
        now = datetime.now(timezone.utc)
        
        # Check Right to Work status
        rtw_expiry = immigration.get("right_to_work_expiry")
        if rtw_expiry:
            try:
                rtw_date = datetime.fromisoformat(rtw_expiry.replace("Z", "+00:00"))
                days_until = (rtw_date - now).days
                
                if days_until < 0:
                    score -= 50
                    issues.append({
                        "type": "rtw_expired",
                        "severity": "critical",
                        "message": f"Right to work expired {abs(days_until)} days ago",
                        "action": "Immediate right to work check required"
                    })
                elif days_until <= 7:
                    score -= 25
                    issues.append({
                        "type": "rtw_expiring_soon",
                        "severity": "high",
                        "message": f"Right to work expires in {days_until} days",
                        "action": "Schedule right to work check immediately"
                    })
                elif days_until <= 30:
                    score -= 10
                    issues.append({
                        "type": "rtw_expiring",
                        "severity": "medium",
                        "message": f"Right to work expires in {days_until} days",
                        "action": "Schedule follow-up right to work check"
                    })
            except (ValueError, TypeError):
                pass
        else:
            # No RTW expiry recorded - check if it's needed
            if visa_type and visa_type not in ["settled", VisaType.SETTLED.value]:
                score -= 15
                issues.append({
                    "type": "rtw_expiry_missing",
                    "severity": "medium",
                    "message": "Right to work expiry date not recorded",
                    "action": "Update employee immigration records"
                })
        
        # Check visa expiry
        visa_end = immigration.get("visa_end_date")
        if visa_end:
            try:
                visa_date = datetime.fromisoformat(visa_end.replace("Z", "+00:00"))
                days_until = (visa_date - now).days
                
                if days_until < 0:
                    score -= 40
                    issues.append({
                        "type": "visa_expired",
                        "severity": "critical",
                        "message": f"Visa expired {abs(days_until)} days ago",
                        "action": "Review employment status immediately"
                    })
                elif days_until <= 30:
                    score -= 20
                    issues.append({
                        "type": "visa_expiring_soon",
                        "severity": "high",
                        "message": f"Visa expires in {days_until} days",
                        "action": "Check if extension application submitted"
                    })
                elif days_until <= 90:
                    score -= 5
                    issues.append({
                        "type": "visa_expiring",
                        "severity": "low",
                        "message": f"Visa expires in {days_until} days",
                        "action": "Monitor visa renewal status"
                    })
            except (ValueError, TypeError):
                pass
        
        # Check passport expiry
        passport_expiry = immigration.get("passport_expiry")
        if passport_expiry:
            try:
                passport_date = datetime.fromisoformat(passport_expiry.replace("Z", "+00:00"))
                days_until = (passport_date - now).days
                
                if days_until < 0:
                    score -= 10
                    issues.append({
                        "type": "passport_expired",
                        "severity": "medium",
                        "message": f"Passport expired {abs(days_until)} days ago",
                        "action": "Request updated passport details"
                    })
                elif days_until <= 90:
                    score -= 5
                    issues.append({
                        "type": "passport_expiring",
                        "severity": "low",
                        "message": f"Passport expires in {days_until} days",
                        "action": "Remind employee to renew passport"
                    })
            except (ValueError, TypeError):
                pass
        
        # Check Appendix D records completeness
        appendix_d_score = self._check_appendix_d_completeness(employee)
        if appendix_d_score < 100:
            missing_pct = 100 - appendix_d_score
            penalty = int(missing_pct * 0.2)  # Max 20 points penalty
            score -= penalty
            issues.append({
                "type": "appendix_d_incomplete",
                "severity": "low" if appendix_d_score >= 80 else "medium",
                "message": f"Appendix D records {appendix_d_score}% complete",
                "action": "Update missing employee records"
            })
        
        # Determine status
        score = max(0, min(100, score))
        if score >= 90:
            status = ComplianceStatus.COMPLIANT.value
        elif score >= 70:
            status = ComplianceStatus.ACTION_REQUIRED.value
        elif score >= 50:
            status = ComplianceStatus.URGENT.value
        else:
            status = ComplianceStatus.EXPIRED.value
        
        return {
            "employee_id": employee_id,
            "score": score,
            "status": status,
            "issues": issues,
            "checked_at": now.isoformat()
        }
    
    def _check_appendix_d_completeness(self, employee: dict) -> int:
        """Check completeness of Appendix D required records"""
        total_fields = 0
        completed_fields = 0
        
        immigration = employee.get("immigration_status", {})
        
        # Check each category
        for category, fields in APPENDIX_D_CATEGORIES.items():
            for field_name in fields:
                total_fields += 1
                
                # Check various locations for the field
                if field_name in employee and employee[field_name]:
                    completed_fields += 1
                elif field_name in immigration and immigration[field_name]:
                    completed_fields += 1
                elif field_name == "job_title" and employee.get("job_title"):
                    completed_fields += 1
                elif field_name == "salary" and employee.get("salary"):
                    completed_fields += 1
                elif field_name == "start_date" and employee.get("start_date"):
                    completed_fields += 1
                elif field_name == "email" and employee.get("email"):
                    completed_fields += 1
        
        return int((completed_fields / total_fields) * 100) if total_fields > 0 else 100
    
    # ==================== COMPANY COMPLIANCE ====================
    
    async def get_company_ukvi_dashboard(self, company_id: str) -> Dict[str, Any]:
        """
        Get UKVI compliance dashboard for a company.
        
        Returns:
        - Overall compliance score
        - Employee breakdown by status
        - Active alerts
        - Pending reportable events
        """
        # Get all employees with immigration data
        employees = await db.employees.find(
            {"company_id": company_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        # Calculate scores for each sponsored employee
        sponsored_employees = []
        compliance_scores = []
        
        for emp in employees:
            immigration = emp.get("immigration_status", {})
            visa_type = immigration.get("visa_type", "")
            
            # Skip British citizens
            if visa_type in ["british_citizen", VisaType.BRITISH_CITIZEN.value]:
                continue
            
            score_data = await self.calculate_employee_compliance_score(
                emp["employee_id"],
                company_id
            )
            
            sponsored_employees.append({
                "employee_id": emp["employee_id"],
                "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}",
                "visa_type": visa_type,
                "score": score_data["score"],
                "status": score_data["status"],
                "issues_count": len(score_data.get("issues", []))
            })
            
            if score_data["status"] != ComplianceStatus.NOT_APPLICABLE.value:
                compliance_scores.append(score_data["score"])
        
        # Calculate overall company score
        overall_score = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 100
        
        # Get status breakdown
        status_breakdown = {
            "compliant": len([e for e in sponsored_employees if e["status"] == ComplianceStatus.COMPLIANT.value]),
            "action_required": len([e for e in sponsored_employees if e["status"] == ComplianceStatus.ACTION_REQUIRED.value]),
            "urgent": len([e for e in sponsored_employees if e["status"] == ComplianceStatus.URGENT.value]),
            "expired": len([e for e in sponsored_employees if e["status"] == ComplianceStatus.EXPIRED.value])
        }
        
        # Get active alerts
        active_alerts = await db.ukvi_alerts.find(
            {"company_id": company_id, "resolved": False},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
        
        # Get pending reportable events
        pending_events = await db.ukvi_reporting_events.find(
            {"company_id": company_id, "reported": False},
            {"_id": 0}
        ).sort("event_date", -1).limit(20).to_list(20)
        
        return {
            "company_id": company_id,
            "overall_score": round(overall_score, 1),
            "total_sponsored_employees": len(sponsored_employees),
            "status_breakdown": status_breakdown,
            "employees_at_risk": [e for e in sponsored_employees if e["status"] in [ComplianceStatus.URGENT.value, ComplianceStatus.EXPIRED.value]],
            "active_alerts": active_alerts,
            "pending_reportable_events": pending_events,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ==================== CHANGE DETECTION ====================
    
    async def detect_reportable_changes(
        self,
        employee_id: str,
        company_id: str,
        old_data: dict,
        new_data: dict
    ) -> List[ReportingEvent]:
        """
        Detect changes that must be reported to UKVI.
        
        Compare old and new employee data to identify reportable events.
        """
        events = []
        now = datetime.now(timezone.utc)
        
        # Salary change
        old_salary = old_data.get("salary", 0)
        new_salary = new_data.get("salary", 0)
        if old_salary != new_salary and new_salary > 0:
            events.append(ReportingEvent(
                event_id=f"ukvi_{uuid.uuid4().hex[:12]}",
                employee_id=employee_id,
                company_id=company_id,
                event_type=UKVIReportingEvent.SALARY_CHANGE,
                event_date=now,
                details={
                    "old_salary": old_salary,
                    "new_salary": new_salary,
                    "change_pct": round(((new_salary - old_salary) / old_salary * 100), 2) if old_salary > 0 else 0
                }
            ))
        
        # Role/Job title change
        old_title = old_data.get("job_title", "")
        new_title = new_data.get("job_title", "")
        if old_title != new_title and new_title:
            events.append(ReportingEvent(
                event_id=f"ukvi_{uuid.uuid4().hex[:12]}",
                employee_id=employee_id,
                company_id=company_id,
                event_type=UKVIReportingEvent.ROLE_CHANGE,
                event_date=now,
                details={
                    "old_title": old_title,
                    "new_title": new_title
                }
            ))
        
        # Work location change
        old_location = old_data.get("work_location", "")
        new_location = new_data.get("work_location", "")
        if old_location != new_location and new_location:
            events.append(ReportingEvent(
                event_id=f"ukvi_{uuid.uuid4().hex[:12]}",
                employee_id=employee_id,
                company_id=company_id,
                event_type=UKVIReportingEvent.LOCATION_CHANGE,
                event_date=now,
                details={
                    "old_location": old_location,
                    "new_location": new_location
                }
            ))
        
        # Contact details change
        old_address = old_data.get("address", "")
        new_address = new_data.get("address", "")
        old_phone = old_data.get("phone", "")
        new_phone = new_data.get("phone", "")
        
        if (old_address != new_address or old_phone != new_phone) and (new_address or new_phone):
            events.append(ReportingEvent(
                event_id=f"ukvi_{uuid.uuid4().hex[:12]}",
                employee_id=employee_id,
                company_id=company_id,
                event_type=UKVIReportingEvent.CONTACT_CHANGE,
                event_date=now,
                details={
                    "old_address": old_address,
                    "new_address": new_address,
                    "old_phone": old_phone,
                    "new_phone": new_phone
                }
            ))
        
        # Employment status change
        old_status = old_data.get("status", "")
        new_status = new_data.get("status", "")
        
        if old_status == "active" and new_status == "terminated":
            events.append(ReportingEvent(
                event_id=f"ukvi_{uuid.uuid4().hex[:12]}",
                employee_id=employee_id,
                company_id=company_id,
                event_type=UKVIReportingEvent.CONTRACT_ENDED,
                event_date=now,
                details={
                    "termination_reason": new_data.get("termination_reason", "Not specified")
                }
            ))
        
        # Store events in database
        for event in events:
            await db.ukvi_reporting_events.insert_one(event.to_dict())
        
        return events
    
    # ==================== ALERTS ====================
    
    async def generate_expiry_alerts(self, company_id: str) -> List[UKVIAlert]:
        """
        Generate alerts for expiring documents and compliance issues.
        
        Should be run daily as a scheduled task.
        """
        alerts = []
        now = datetime.now(timezone.utc)
        
        employees = await db.employees.find(
            {"company_id": company_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        for emp in employees:
            immigration = emp.get("immigration_status", {})
            visa_type = immigration.get("visa_type", "")
            
            # Skip British citizens
            if visa_type in ["british_citizen", VisaType.BRITISH_CITIZEN.value]:
                continue
            
            employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
            
            # Check visa expiry
            visa_end = immigration.get("visa_end_date")
            if visa_end:
                try:
                    visa_date = datetime.fromisoformat(visa_end.replace("Z", "+00:00"))
                    days_until = (visa_date - now).days
                    
                    if days_until in self.visa_expiry_warning_days or days_until < min(self.visa_expiry_warning_days):
                        severity = "critical" if days_until <= 7 else "high" if days_until <= 30 else "medium"
                        
                        alert = UKVIAlert(
                            alert_id=f"alert_{uuid.uuid4().hex[:12]}",
                            employee_id=emp["employee_id"],
                            company_id=company_id,
                            alert_type="visa_expiry",
                            severity=severity,
                            title=f"Visa expiring: {employee_name}",
                            description=f"Visa expires in {days_until} days on {visa_end}",
                            action_required="Check extension application status or review employment continuation",
                            deadline=visa_date
                        )
                        alerts.append(alert)
                except (ValueError, TypeError):
                    pass
            
            # Check RTW expiry
            rtw_expiry = immigration.get("right_to_work_expiry")
            if rtw_expiry:
                try:
                    rtw_date = datetime.fromisoformat(rtw_expiry.replace("Z", "+00:00"))
                    days_until = (rtw_date - now).days
                    
                    if days_until in self.rtw_check_warning_days or days_until < min(self.rtw_check_warning_days):
                        severity = "critical" if days_until <= 1 else "high" if days_until <= 7 else "medium"
                        
                        alert = UKVIAlert(
                            alert_id=f"alert_{uuid.uuid4().hex[:12]}",
                            employee_id=emp["employee_id"],
                            company_id=company_id,
                            alert_type="rtw_check_due",
                            severity=severity,
                            title=f"RTW check due: {employee_name}",
                            description=f"Right to work check due in {days_until} days",
                            action_required="Perform follow-up right to work check",
                            deadline=rtw_date
                        )
                        alerts.append(alert)
                except (ValueError, TypeError):
                    pass
        
        # Store new alerts (check for duplicates)
        for alert in alerts:
            existing = await db.ukvi_alerts.find_one({
                "employee_id": alert.employee_id,
                "alert_type": alert.alert_type,
                "resolved": False
            })
            
            if not existing:
                await db.ukvi_alerts.insert_one(alert.to_dict())

                # Send email notification to company owner / HR team (best-effort)
                try:
                    emp = await db.employees.find_one(
                        {"employee_id": alert.employee_id}, {"_id": 0}
                    ) or {}
                    company = await db.companies.find_one(
                        {"company_id": company_id}, {"_id": 0}
                    ) or {}
                    owner_user = None
                    if company.get("owner_id"):
                        owner_user = await db.users.find_one(
                            {"user_id": company["owner_id"]}, {"_id": 0}
                        )

                    recipient_email = (owner_user or {}).get("email") or emp.get("email")
                    if recipient_email and alert.alert_type == "visa_expiry":
                        from services.email_service import email_service
                        deadline_iso = alert.deadline.isoformat() if alert.deadline else ""
                        days_left = (alert.deadline - now).days if alert.deadline else 0
                        await email_service.send_visa_expiry_alert(
                            to=recipient_email,
                            employee_name=f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                            visa_type=(emp.get('immigration_status') or {}).get('visa_type', 'Unknown'),
                            expiry_date=deadline_iso[:10],
                            days_until=max(0, days_left),
                            manager_name=(owner_user or {}).get("name")
                        )
                except Exception as exc:
                    import logging as _logging
                    _logging.getLogger(__name__).warning(f"Visa expiry email failed: {exc}")

        # Salary threshold monitoring for sponsored workers (UKVI requirement)
        # Sponsored workers must be paid at or above the SOC code going-rate / £38,700
        SPONSORED_VISA_TYPES = {"skilled_worker", "tier2", "gbm", "scale_up", "intra_company"}
        DEFAULT_SKILLED_WORKER_THRESHOLD = 38700  # 2024/25 base threshold
        for emp in employees:
            immigration = emp.get("immigration_status", {}) or {}
            if immigration.get("visa_type") not in SPONSORED_VISA_TYPES:
                continue
            salary = float(emp.get("salary", 0) or 0)
            if salary <= 0:
                continue
            cos = await db.cos_register.find_one(
                {"employee_id": emp["employee_id"], "company_id": company_id},
                {"_id": 0, "going_rate_annual": 1, "salary": 1}
            ) or {}
            going_rate = cos.get("going_rate_annual") or DEFAULT_SKILLED_WORKER_THRESHOLD
            if salary < going_rate:
                deficit = going_rate - salary
                alert_id = f"alert_{uuid.uuid4().hex[:12]}"
                existing = await db.ukvi_alerts.find_one({
                    "employee_id": emp["employee_id"],
                    "alert_type": "salary_threshold_breach",
                    "resolved": False,
                })
                if not existing:
                    await db.ukvi_alerts.insert_one({
                        "alert_id": alert_id,
                        "employee_id": emp["employee_id"],
                        "company_id": company_id,
                        "alert_type": "salary_threshold_breach",
                        "severity": "high",
                        "title": f"Salary below sponsor threshold: {emp.get('first_name', '')} {emp.get('last_name', '')}",
                        "description": (
                            f"Annual salary £{salary:,.0f} is below the going-rate / threshold £{going_rate:,.0f} "
                            f"(deficit £{deficit:,.0f}). Risk to sponsor licence."
                        ),
                        "action_required": "Review CoS, increase salary, or reassess sponsorship",
                        "deadline": None,
                        "resolved": False,
                        "created_at": now.isoformat(),
                    })

        return alerts
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_note: str
    ) -> dict:
        """Mark an alert as resolved"""
        now = datetime.now(timezone.utc)
        
        result = await db.ukvi_alerts.update_one(
            {"alert_id": alert_id},
            {"$set": {
                "resolved": True,
                "resolved_at": now.isoformat(),
                "resolved_by": resolved_by,
                "resolution_note": resolution_note
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Alert {alert_id} not found")
        
        return {"status": "resolved", "alert_id": alert_id}
    
    # ==================== REPORTING ====================
    
    async def mark_event_reported(
        self,
        event_id: str,
        sms_reference: str,
        reported_by: str
    ) -> dict:
        """Mark a reportable event as reported to UKVI"""
        now = datetime.now(timezone.utc)
        
        result = await db.ukvi_reporting_events.update_one(
            {"event_id": event_id},
            {"$set": {
                "reported": True,
                "reported_date": now.isoformat(),
                "sms_reference": sms_reference,
                "reported_by": reported_by
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Event {event_id} not found")
        
        return {"status": "reported", "event_id": event_id, "sms_reference": sms_reference}
    
    async def get_reporting_checklist(self, company_id: str) -> Dict[str, Any]:
        """
        Get checklist of pending UKVI reports.
        
        Groups events by type and calculates days remaining to report.
        """
        pending_events = await db.ukvi_reporting_events.find(
            {"company_id": company_id, "reported": False},
            {"_id": 0}
        ).to_list(100)
        
        now = datetime.now(timezone.utc)
        checklist = []
        
        for event in pending_events:
            event_date = datetime.fromisoformat(event["event_date"].replace("Z", "+00:00"))
            
            # Calculate working days since event (10 working days deadline)
            days_since = (now - event_date).days
            working_days_elapsed = int(days_since * 5 / 7)  # Approximate
            working_days_remaining = max(0, 10 - working_days_elapsed)
            
            # Get employee name
            employee = await db.employees.find_one(
                {"employee_id": event["employee_id"]},
                {"first_name": 1, "last_name": 1, "_id": 0}
            )
            employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}" if employee else "Unknown"
            
            checklist.append({
                "event_id": event["event_id"],
                "employee_name": employee_name,
                "event_type": event["event_type"],
                "event_date": event["event_date"],
                "days_since_event": days_since,
                "working_days_remaining": working_days_remaining,
                "urgency": "overdue" if working_days_remaining <= 0 else "urgent" if working_days_remaining <= 3 else "normal",
                "details": event.get("details", {})
            })
        
        # Sort by urgency
        checklist.sort(key=lambda x: x["working_days_remaining"])
        
        return {
            "company_id": company_id,
            "pending_reports": len(checklist),
            "overdue_reports": len([c for c in checklist if c["urgency"] == "overdue"]),
            "checklist": checklist,
            "checked_at": now.isoformat()
        }


# Singleton instance
ukvi_service = UKVIComplianceService()
