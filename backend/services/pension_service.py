"""
RealtouchHR - Pension Auto-Enrolment Service
UK Workplace Pension Compliance

The Pensions Act 2008 requires all UK employers to automatically enrol eligible workers
into a qualifying workplace pension. This service handles:
- Auto-enrolment assessment
- Pension scheme management
- Contribution calculations
- Re-enrolment tracking
"""

import os
import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid
from decimal import Decimal

from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
logger = logging.getLogger(__name__)


# ==================== CONSTANTS ====================

# Auto-enrolment thresholds (2025-26 tax year)
LOWER_QUALIFYING_EARNINGS = 6240  # Annual
EARNINGS_TRIGGER = 10000  # Annual
UPPER_QUALIFYING_EARNINGS = 50270  # Annual

# State pension ages (simplified)
STATE_PENSION_AGE = 67

# Minimum contribution rates
MIN_EMPLOYER_CONTRIBUTION = 3.0  # 3%
MIN_EMPLOYEE_CONTRIBUTION = 5.0  # 5% (includes tax relief)
MIN_TOTAL_CONTRIBUTION = 8.0  # 8%


# ==================== ENUMS ====================

class PensionSchemeType(str, Enum):
    DEFINED_CONTRIBUTION = "defined_contribution"
    DEFINED_BENEFIT = "defined_benefit"
    HYBRID = "hybrid"


class QualifyingBasis(str, Enum):
    QUALIFYING_EARNINGS = "qualifying_earnings"  # Earnings between thresholds
    PENSIONABLE_PAY = "pensionable_pay"  # Basic pay
    TOTAL_PAY = "total_pay"  # All earnings


class EnrolmentStatus(str, Enum):
    ELIGIBLE = "eligible"  # Should be auto-enrolled
    ENROLLED = "enrolled"  # Currently enrolled
    OPTED_OUT = "opted_out"  # Opted out within 1 month
    POSTPONED = "postponed"  # Postponement applied
    NOT_ELIGIBLE = "not_eligible"  # Doesn't meet criteria
    ENTITLED_WORKER = "entitled_worker"  # Can join but not auto-enrolled
    CEASED = "ceased"  # Membership ceased


class WorkerCategory(str, Enum):
    ELIGIBLE_JOBHOLDER = "eligible_jobholder"  # Must be auto-enrolled
    NON_ELIGIBLE_JOBHOLDER = "non_eligible_jobholder"  # Can opt in
    ENTITLED_WORKER = "entitled_worker"  # Can join


# ==================== DATA CLASSES ====================

@dataclass
class PensionScheme:
    """A workplace pension scheme"""
    scheme_id: str
    company_id: str
    scheme_name: str
    provider: str
    employer_reference: str  # Employer's reference with provider
    pension_type: PensionSchemeType
    employer_rate: float
    employee_rate: float
    qualifying_basis: QualifyingBasis
    is_default: bool = False
    staging_date: Optional[date] = None  # Company's AE duties start date
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "scheme_id": self.scheme_id,
            "company_id": self.company_id,
            "scheme_name": self.scheme_name,
            "provider": self.provider,
            "employer_reference": self.employer_reference,
            "pension_type": self.pension_type.value if isinstance(self.pension_type, PensionSchemeType) else self.pension_type,
            "employer_rate": self.employer_rate,
            "employee_rate": self.employee_rate,
            "qualifying_basis": self.qualifying_basis.value if isinstance(self.qualifying_basis, QualifyingBasis) else self.qualifying_basis,
            "is_default": self.is_default,
            "staging_date": self.staging_date.isoformat() if self.staging_date else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EmployeePensionEnrolment:
    """Employee pension enrolment record"""
    enrolment_id: str
    employee_id: str
    company_id: str
    scheme_id: str
    status: EnrolmentStatus
    enrolment_date: Optional[date] = None
    opt_out_date: Optional[date] = None
    opt_out_reference: Optional[str] = None
    postponement_end_date: Optional[date] = None
    re_enrolment_due_date: Optional[date] = None  # 3-yearly
    employee_rate: Optional[float] = None  # Override
    employer_rate: Optional[float] = None  # Override
    worker_category: Optional[WorkerCategory] = None
    # Enrolment is recorded internally only — no live pension provider (e.g. NEST) or
    # Pensions Regulator Declaration of Compliance integration exists yet.
    enrolment_recorded_locally: bool = True
    provider_confirmed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "enrolment_id": self.enrolment_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "scheme_id": self.scheme_id,
            "status": self.status.value if isinstance(self.status, EnrolmentStatus) else self.status,
            "enrolment_date": self.enrolment_date.isoformat() if self.enrolment_date else None,
            "opt_out_date": self.opt_out_date.isoformat() if self.opt_out_date else None,
            "opt_out_reference": self.opt_out_reference,
            "postponement_end_date": self.postponement_end_date.isoformat() if self.postponement_end_date else None,
            "re_enrolment_due_date": self.re_enrolment_due_date.isoformat() if self.re_enrolment_due_date else None,
            "employee_rate": self.employee_rate,
            "employer_rate": self.employer_rate,
            "worker_category": self.worker_category.value if isinstance(self.worker_category, WorkerCategory) else self.worker_category,
            "enrolment_recorded_locally": self.enrolment_recorded_locally,
            "provider_confirmed": self.provider_confirmed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== PENSION SERVICE ====================

class PensionService:
    """Service for pension auto-enrolment management"""
    
    def __init__(self):
        self.lower_threshold = LOWER_QUALIFYING_EARNINGS
        self.trigger_threshold = EARNINGS_TRIGGER
        self.upper_threshold = UPPER_QUALIFYING_EARNINGS
        self.state_pension_age = STATE_PENSION_AGE
    
    # ==================== PENSION SCHEMES ====================
    
    async def create_scheme(
        self,
        company_id: str,
        scheme_name: str,
        provider: str,
        employer_reference: str,
        pension_type: str,
        employer_contribution_pct: float,
        employee_contribution_pct: float,
        qualifying_basis: str = "qualifying_earnings",
        is_default: bool = False,
        staging_date: Optional[date] = None
    ) -> PensionScheme:
        """Create a new pension scheme"""
        # Validate minimum contributions
        total_contribution = employer_contribution_pct + employee_contribution_pct
        if employer_contribution_pct < MIN_EMPLOYER_CONTRIBUTION:
            raise ValueError(f"Employer contribution must be at least {MIN_EMPLOYER_CONTRIBUTION}%")
        if total_contribution < MIN_TOTAL_CONTRIBUTION:
            raise ValueError(f"Total contribution must be at least {MIN_TOTAL_CONTRIBUTION}%")
        
        # If this is default, unset other defaults
        if is_default:
            await db.pension_schemes.update_many(
                {"company_id": company_id},
                {"$set": {"is_default": False}}
            )
        
        scheme = PensionScheme(
            scheme_id=f"scheme_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            scheme_name=scheme_name,
            provider=provider,
            employer_reference=employer_reference,
            pension_type=PensionSchemeType(pension_type),
            employer_rate=employer_contribution_pct,
            employee_rate=employee_contribution_pct,
            qualifying_basis=QualifyingBasis(qualifying_basis),
            is_default=is_default,
            staging_date=staging_date
        )
        
        await db.pension_schemes.insert_one(scheme.to_dict())
        
        return scheme
    
    async def get_schemes(self, company_id: str) -> List[dict]:
        """Get all pension schemes for a company"""
        schemes = await db.pension_schemes.find(
            {"company_id": company_id},
            {"_id": 0}
        ).to_list(100)
        
        return schemes
    
    async def get_default_scheme(self, company_id: str) -> Optional[dict]:
        """Get the default pension scheme"""
        scheme = await db.pension_schemes.find_one(
            {"company_id": company_id, "is_default": True},
            {"_id": 0}
        )
        return scheme
    
    async def update_scheme(
        self,
        scheme_id: str,
        company_id: str,
        updates: dict
    ) -> dict:
        """Update a pension scheme"""
        now = datetime.now(timezone.utc)
        updates["updated_at"] = now.isoformat()
        
        # Handle default toggle
        if updates.get("is_default"):
            await db.pension_schemes.update_many(
                {"company_id": company_id, "scheme_id": {"$ne": scheme_id}},
                {"$set": {"is_default": False}}
            )
        
        result = await db.pension_schemes.update_one(
            {"scheme_id": scheme_id, "company_id": company_id},
            {"$set": updates}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Scheme {scheme_id} not found")
        
        return {"status": "updated", "scheme_id": scheme_id}
    
    # ==================== AUTO-ENROLMENT ASSESSMENT ====================
    
    def assess_worker_category(
        self,
        annual_earnings: float,
        age: int
    ) -> WorkerCategory:
        """
        Assess worker category for auto-enrolment.
        
        Categories:
        - Eligible Jobholder: Age 22 to state pension age, earning above trigger (£10k)
        - Non-Eligible Jobholder: Age 16-74, earning between thresholds OR 16-21/SPA-74 above trigger
        - Entitled Worker: Age 16-74, earning below lower threshold (£6,240)
        """
        if age < 16 or age > 74:
            return WorkerCategory.ENTITLED_WORKER  # Not actually entitled, but minimal category
        
        # Eligible Jobholder: Age 22-SPA and earning above trigger
        if 22 <= age < self.state_pension_age and annual_earnings >= self.trigger_threshold:
            return WorkerCategory.ELIGIBLE_JOBHOLDER
        
        # Non-Eligible Jobholder scenarios
        if (annual_earnings >= self.lower_threshold and annual_earnings < self.trigger_threshold) or \
           ((age >= 16 and age < 22) or (age >= self.state_pension_age and age <= 74)) and annual_earnings >= self.trigger_threshold:
            return WorkerCategory.NON_ELIGIBLE_JOBHOLDER
        
        # Entitled Worker: earning below lower threshold
        return WorkerCategory.ENTITLED_WORKER
    
    async def assess_employee_enrolment(
        self,
        employee_id: str,
        company_id: str,
        annual_earnings: float
    ) -> dict:
        """
        Assess an employee for auto-enrolment.
        
        Returns the worker category and recommended action.
        """
        # Get employee details
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # Calculate age
        dob_str = employee.get("date_of_birth")
        if dob_str:
            dob = date.fromisoformat(dob_str)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            age = 30  # Assume working age if DOB not known
        
        # Assess category
        category = self.assess_worker_category(annual_earnings, age)
        
        # Check current enrolment status
        current_enrolment = await db.pension_enrolments.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        
        # Determine action
        if category == WorkerCategory.ELIGIBLE_JOBHOLDER:
            if not current_enrolment or current_enrolment.get("status") in [
                EnrolmentStatus.NOT_ELIGIBLE.value, None
            ]:
                action = "auto_enrol"
                message = "Employee must be auto-enrolled"
            elif current_enrolment.get("status") == EnrolmentStatus.OPTED_OUT.value:
                # Check if opt-out window has expired (can re-enrol after 3 years)
                opt_out_date_str = current_enrolment.get("opt_out_date")
                if opt_out_date_str:
                    opt_out_date = date.fromisoformat(opt_out_date_str)
                    if (date.today() - opt_out_date).days > 1095:  # ~3 years
                        action = "re_enrol"
                        message = "Employee due for re-enrolment"
                    else:
                        action = "no_action"
                        message = "Employee opted out, re-enrolment not yet due"
                else:
                    action = "no_action"
                    message = "Employee opted out"
            else:
                action = "no_action"
                message = "Employee already enrolled"
        elif category == WorkerCategory.NON_ELIGIBLE_JOBHOLDER:
            action = "inform"
            message = "Employee can opt in to pension"
        else:
            action = "inform"
            message = "Employee can join pension scheme"
        
        return {
            "employee_id": employee_id,
            "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
            "age": age,
            "annual_earnings": annual_earnings,
            "worker_category": category.value,
            "current_status": current_enrolment.get("status") if current_enrolment else None,
            "action": action,
            "message": message
        }
    
    async def run_bulk_assessment(
        self,
        company_id: str,
        pay_run_id: Optional[str] = None
    ) -> dict:
        """
        Run auto-enrolment assessment for all employees.
        
        If pay_run_id provided, uses earnings from that pay run.
        Otherwise estimates from base salary.
        """
        employees = await db.employees.find(
            {"company_id": company_id, "status": "active"},
            {"_id": 0}
        ).to_list(10000)
        
        results = {
            "eligible_jobholders": [],
            "non_eligible_jobholders": [],
            "entitled_workers": [],
            "already_enrolled": [],
            "to_enrol": []
        }
        
        for emp in employees:
            # Estimate annual earnings
            salary = emp.get("salary", 0)
            annual_earnings = salary  # Assuming annual salary is stored
            
            assessment = await self.assess_employee_enrolment(
                emp["employee_id"],
                company_id,
                annual_earnings
            )
            
            category = assessment["worker_category"]
            
            if category == WorkerCategory.ELIGIBLE_JOBHOLDER.value:
                results["eligible_jobholders"].append(assessment)
                if assessment["action"] in ["auto_enrol", "re_enrol"]:
                    results["to_enrol"].append(assessment)
                elif assessment["action"] == "no_action" and assessment.get("current_status") == EnrolmentStatus.ENROLLED.value:
                    results["already_enrolled"].append(assessment)
            elif category == WorkerCategory.NON_ELIGIBLE_JOBHOLDER.value:
                results["non_eligible_jobholders"].append(assessment)
            else:
                results["entitled_workers"].append(assessment)
        
        return {
            "total_assessed": len(employees),
            "eligible_jobholders_count": len(results["eligible_jobholders"]),
            "non_eligible_count": len(results["non_eligible_jobholders"]),
            "entitled_workers_count": len(results["entitled_workers"]),
            "already_enrolled_count": len(results["already_enrolled"]),
            "to_enrol_count": len(results["to_enrol"]),
            "details": results
        }
    
    # ==================== ENROLMENT ====================
    
    async def enrol_employee(
        self,
        employee_id: str,
        company_id: str,
        scheme_id: Optional[str] = None,
        employee_contribution_override: Optional[float] = None,
        employer_contribution_override: Optional[float] = None
    ) -> EmployeePensionEnrolment:
        """Enrol an employee in a pension scheme"""
        # Get scheme (use default if not specified)
        if scheme_id:
            scheme = await db.pension_schemes.find_one(
                {"scheme_id": scheme_id, "company_id": company_id},
                {"_id": 0}
            )
        else:
            scheme = await self.get_default_scheme(company_id)
        
        if not scheme:
            raise ValueError("No pension scheme found")
        
        # Check for existing enrolment
        existing = await db.pension_enrolments.find_one(
            {"employee_id": employee_id, "company_id": company_id}
        )
        
        today = date.today()
        re_enrolment_date = today + timedelta(days=1095)  # ~3 years
        
        enrolment = EmployeePensionEnrolment(
            enrolment_id=f"enrol_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            scheme_id=scheme["scheme_id"],
            status=EnrolmentStatus.ENROLLED,
            enrolment_date=today,
            re_enrolment_due_date=re_enrolment_date,
            employee_rate=employee_contribution_override,
            employer_rate=employer_contribution_override,
            worker_category=WorkerCategory.ELIGIBLE_JOBHOLDER
        )
        
        if existing:
            await db.pension_enrolments.update_one(
                {"employee_id": employee_id, "company_id": company_id},
                {"$set": enrolment.to_dict()}
            )
        else:
            await db.pension_enrolments.insert_one(enrolment.to_dict())
        
        # Update employee record — recorded internally only. No live pension provider
        # (e.g. NEST) or Pensions Regulator Declaration of Compliance integration exists
        # yet, so provider_confirmed stays False until that integration is connected.
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "pension_enrolled": True,
                "pension_scheme_id": scheme["scheme_id"],
                "pension_enrolment_date": today.isoformat(),
                "pension_enrolment_recorded_locally": True,
                "pension_provider_confirmed": False
            }}
        )

        # Send enrolment confirmation email (best-effort) — only once a real pension
        # provider has confirmed enrolment. Until then, sending a "you are enrolled"
        # email would misrepresent an internal record as a completed legal enrolment.
        if enrolment.provider_confirmed:
            try:
                emp = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0}) or {}
                if emp.get("email"):
                    from services.email_service import email_service
                    opt_out_end = (today + timedelta(days=30)).isoformat()
                    await email_service.send_pension_enrolment(
                        to=emp["email"],
                        employee_name=f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                        scheme_name=scheme.get("name", scheme.get("scheme_name", "Workplace Pension")),
                        enrolment_date=today.isoformat(),
                        employee_contribution_pct=(employee_contribution_override
                                                   or scheme.get("employee_rate", 5.0)),
                        employer_contribution_pct=(employer_contribution_override
                                                   or scheme.get("employer_rate", 3.0)),
                        opt_out_window_end=opt_out_end,
                    )
            except Exception as exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(f"Pension enrolment email failed: {exc}")

        return enrolment
    
    async def record_opt_out(
        self,
        employee_id: str,
        company_id: str,
        opt_out_reference: str
    ) -> dict:
        """Record an employee opt-out"""
        today = date.today()
        
        # Get current enrolment
        enrolment = await db.pension_enrolments.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not enrolment:
            raise ValueError("No enrolment found")
        
        # Validate opt-out window (1 month from enrolment)
        enrolment_date_str = enrolment.get("enrolment_date")
        if enrolment_date_str:
            enrolment_date = date.fromisoformat(enrolment_date_str)
            if (today - enrolment_date).days > 30:
                raise ValueError("Opt-out window has expired (must be within 1 month of enrolment)")
        
        now = datetime.now(timezone.utc)
        
        await db.pension_enrolments.update_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"$set": {
                "status": EnrolmentStatus.OPTED_OUT.value,
                "opt_out_date": today.isoformat(),
                "opt_out_reference": opt_out_reference,
                "updated_at": now.isoformat()
            }}
        )
        
        # Update employee record
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": {"pension_enrolled": False}}
        )
        
        return {
            "status": "opted_out",
            "employee_id": employee_id,
            "opt_out_date": today.isoformat()
        }
    
    async def get_enrolments(
        self,
        company_id: str,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get all pension enrolments for a company"""
        query = {"company_id": company_id}
        if status:
            query["status"] = status
        
        enrolments = await db.pension_enrolments.find(
            query, {"_id": 0}
        ).to_list(10000)
        
        # Enrich with employee names
        for enrolment in enrolments:
            emp = await db.employees.find_one(
                {"employee_id": enrolment["employee_id"]},
                {"first_name": 1, "last_name": 1, "_id": 0}
            )
            if emp:
                enrolment["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        
        return enrolments
    
    # ==================== CONTRIBUTION CALCULATION ====================
    
    def calculate_contributions(
        self,
        gross_pay: float,
        scheme: dict,
        qualifying_basis: str = "qualifying_earnings"
    ) -> dict:
        """
        Calculate pension contributions for a pay period.
        
        Qualifying earnings = gross pay between £520/month and £4,189/month (2025-26)
        """
        # Monthly thresholds
        monthly_lower = self.lower_threshold / 12
        monthly_upper = self.upper_threshold / 12
        
        # Calculate pensionable earnings
        if qualifying_basis == "qualifying_earnings":
            pensionable = max(0, min(gross_pay, monthly_upper) - monthly_lower)
        elif qualifying_basis == "total_pay":
            pensionable = gross_pay
        else:  # pensionable_pay (basic pay)
            pensionable = gross_pay
        
        employee_pct = scheme.get("employee_rate", MIN_EMPLOYEE_CONTRIBUTION)
        employer_pct = scheme.get("employer_rate", MIN_EMPLOYER_CONTRIBUTION)
        
        employee_contribution = round(pensionable * (employee_pct / 100), 2)
        employer_contribution = round(pensionable * (employer_pct / 100), 2)
        
        return {
            "gross_pay": gross_pay,
            "pensionable_earnings": round(pensionable, 2),
            "employee_contribution_pct": employee_pct,
            "employer_contribution_pct": employer_pct,
            "employee_contribution": employee_contribution,
            "employer_contribution": employer_contribution,
            "total_contribution": employee_contribution + employer_contribution
        }
    
    async def get_contribution_report(
        self,
        company_id: str,
        pay_run_id: str
    ) -> dict:
        """Generate pension contribution report for a pay run"""
        # Get pay run
        pay_run = await db.pay_runs.find_one(
            {"payrun_id": pay_run_id, "company_id": company_id},
            {"_id": 0}
        )

        if not pay_run:
            raise ValueError("Pay run not found")

        # Get default scheme
        scheme = await self.get_default_scheme(company_id)

        if not scheme:
            return {
                "pay_run_id": pay_run_id,
                "error": "No pension scheme configured"
            }

        # Get enrolled employees
        enrolled = await self.get_enrolments(company_id, EnrolmentStatus.ENROLLED.value)
        enrolled_ids = {e["employee_id"] for e in enrolled}

        # Calculate contributions for each enrolled employee in pay run
        payslips = await db.payslips.find({"payrun_id": pay_run_id}, {"_id": 0}).to_list(10000)
        contributions = []
        total_employee = 0
        total_employer = 0

        for payslip in payslips:
            if payslip.get("employee_id") in enrolled_ids:
                gross = payslip.get("gross_pay", 0)
                calc = self.calculate_contributions(gross, scheme)
                emp = await db.employees.find_one(
                    {"employee_id": payslip["employee_id"]},
                    {"first_name": 1, "last_name": 1, "_id": 0}
                )
                employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() if emp else ""

                contributions.append({
                    "employee_id": payslip["employee_id"],
                    "employee_name": employee_name,
                    **calc
                })

                total_employee += calc["employee_contribution"]
                total_employer += calc["employer_contribution"]

        return {
            "pay_run_id": pay_run_id,
            "period": f"{pay_run.get('period_start', '')} - {pay_run.get('period_end', '')}",
            "scheme_name": scheme["scheme_name"],
            "provider": scheme["provider"],
            "employee_contributions_total": round(total_employee, 2),
            "employer_contributions_total": round(total_employer, 2),
            "total_contributions": round(total_employee + total_employer, 2),
            "enrolled_employees": len(contributions),
            "contributions": contributions
        }


# Singleton instance
pension_service = PensionService()
