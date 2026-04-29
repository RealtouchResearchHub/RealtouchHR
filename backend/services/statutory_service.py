"""
RealtouchHR - Statutory Payments Service
SSP, SMP, SPP, ShPP, SAP Calculations

UK statutory payments are legally required payments that employers must make
to employees in certain circumstances. This service calculates:
- SSP (Statutory Sick Pay)
- SMP (Statutory Maternity Pay)
- SPP (Statutory Paternity Pay)
- ShPP (Shared Parental Pay)
- SAP (Statutory Adoption Pay)
"""

import os
import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid
from decimal import Decimal

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


# ==================== 2025-26 TAX YEAR RATES ====================

# Statutory payment rates (updated annually)
SSP_WEEKLY_RATE = 116.75  # Weekly SSP rate
SSP_WAITING_DAYS = 3  # First 3 qualifying days are waiting days
SSP_MAX_WEEKS = 28  # Maximum 28 weeks of SSP

SMP_FIRST_6_WEEKS_RATE = 0.90  # 90% of average weekly earnings
SMP_STANDARD_WEEKLY_RATE = 184.03  # Or 90% of AWE if lower
SMP_TOTAL_WEEKS = 39  # 39 weeks total

SPP_WEEKLY_RATE = 184.03  # Or 90% of AWE if lower
SPP_MAX_WEEKS = 2  # 1 or 2 weeks paternity

SHPP_WEEKLY_RATE = 184.03  # Or 90% of AWE if lower
SHPP_MAX_WEEKS = 37  # Max shared parental (derived from SMP)

SAP_FIRST_6_WEEKS_RATE = 0.90  # 90% of AWE
SAP_STANDARD_WEEKLY_RATE = 184.03  # Or 90% of AWE if lower
SAP_TOTAL_WEEKS = 39  # 39 weeks total

# Lower Earnings Limit for qualifying
LOWER_EARNINGS_LIMIT = 123.00  # Weekly

# Recovery rates
SMALL_EMPLOYER_RECOVERY_RATE = 1.03  # 103% for small employers
STANDARD_RECOVERY_RATE = 0.92  # 92% for standard employers


# ==================== ENUMS ====================

class StatutoryPaymentType(str, Enum):
    SSP = "ssp"
    SMP = "smp"
    SPP = "spp"
    SHPP = "shpp"
    SAP = "sap"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==================== DATA CLASSES ====================

@dataclass
class StatutoryPayment:
    """A statutory payment record"""
    payment_id: str
    employee_id: str
    company_id: str
    payment_type: StatutoryPaymentType
    start_date: date
    end_date: Optional[date] = None
    qualifying_week: Optional[date] = None  # For SMP/SAP
    average_weekly_earnings: float = 0
    weeks_paid: float = 0
    weeks_remaining: float = 0
    amount_paid: float = 0
    amount_recoverable: float = 0
    recovery_rate: float = STANDARD_RECOVERY_RATE
    recovery_claimed: bool = False
    status: PaymentStatus = PaymentStatus.PENDING
    linked_pay_run_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "payment_type": self.payment_type.value if isinstance(self.payment_type, StatutoryPaymentType) else self.payment_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "qualifying_week": self.qualifying_week.isoformat() if self.qualifying_week else None,
            "average_weekly_earnings": self.average_weekly_earnings,
            "weeks_paid": self.weeks_paid,
            "weeks_remaining": self.weeks_remaining,
            "amount_paid": self.amount_paid,
            "amount_recoverable": self.amount_recoverable,
            "recovery_rate": self.recovery_rate,
            "recovery_claimed": self.recovery_claimed,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else self.status,
            "linked_pay_run_ids": self.linked_pay_run_ids,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== STATUTORY PAYMENTS SERVICE ====================

class StatutoryPaymentsService:
    """Service for statutory payment calculations"""
    
    def __init__(self):
        pass
    
    # ==================== SSP CALCULATIONS ====================
    
    async def calculate_ssp(
        self,
        employee_id: str,
        company_id: str,
        sick_start_date: date,
        sick_end_date: date,
        qualifying_days_per_week: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate Statutory Sick Pay.
        
        SSP is paid for qualifying days after 3 waiting days.
        Maximum 28 weeks of SSP.
        """
        # Get employee to check eligibility
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # Calculate average weekly earnings (simplified - use last 8 weeks)
        awe = await self._calculate_average_weekly_earnings(employee_id, company_id)
        
        # Check if earnings meet lower limit
        if awe < LOWER_EARNINGS_LIMIT:
            return {
                "eligible": False,
                "reason": f"Average weekly earnings (£{awe:.2f}) below lower earnings limit (£{LOWER_EARNINGS_LIMIT})",
                "amount": 0
            }
        
        # Calculate total sick days
        total_days = (sick_end_date - sick_start_date).days + 1
        
        # Calculate qualifying days (excluding waiting days)
        # Simplified: assume qualifying days = working days in period
        total_weeks = total_days / 7
        qualifying_days = max(0, (total_weeks * qualifying_days_per_week) - SSP_WAITING_DAYS)
        
        # Cap at 28 weeks
        max_qualifying_days = SSP_MAX_WEEKS * qualifying_days_per_week
        qualifying_days = min(qualifying_days, max_qualifying_days)
        
        # Calculate SSP amount
        daily_rate = SSP_WEEKLY_RATE / qualifying_days_per_week
        ssp_amount = qualifying_days * daily_rate
        
        weeks_of_ssp = qualifying_days / qualifying_days_per_week
        
        return {
            "eligible": True,
            "payment_type": "ssp",
            "sick_start_date": sick_start_date.isoformat(),
            "sick_end_date": sick_end_date.isoformat(),
            "total_sick_days": total_days,
            "waiting_days": min(SSP_WAITING_DAYS, total_days),
            "qualifying_days": round(qualifying_days, 1),
            "weeks_of_ssp": round(weeks_of_ssp, 2),
            "weekly_rate": SSP_WEEKLY_RATE,
            "daily_rate": round(daily_rate, 2),
            "total_ssp_amount": round(ssp_amount, 2),
            "average_weekly_earnings": round(awe, 2)
        }
    
    # ==================== SMP CALCULATIONS ====================
    
    async def calculate_smp(
        self,
        employee_id: str,
        company_id: str,
        expected_week_of_childbirth: date,
        maternity_start_date: date,
        is_small_employer: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate Statutory Maternity Pay.
        
        SMP is paid for up to 39 weeks:
        - First 6 weeks: 90% of AWE
        - Remaining 33 weeks: £184.03 or 90% of AWE if lower
        """
        # Calculate qualifying week (15 weeks before EWC)
        qualifying_week = expected_week_of_childbirth - timedelta(weeks=15)
        
        # Calculate average weekly earnings
        awe = await self._calculate_average_weekly_earnings(employee_id, company_id)
        
        # Check eligibility
        if awe < LOWER_EARNINGS_LIMIT:
            return {
                "eligible": False,
                "reason": f"Average weekly earnings (£{awe:.2f}) below lower earnings limit (£{LOWER_EARNINGS_LIMIT})"
            }
        
        # Calculate first 6 weeks (90% of AWE)
        first_6_weeks_rate = awe * SMP_FIRST_6_WEEKS_RATE
        first_6_weeks_total = first_6_weeks_rate * 6
        
        # Calculate remaining 33 weeks (lower of statutory rate or 90% of AWE)
        remaining_rate = min(SMP_STANDARD_WEEKLY_RATE, awe * 0.90)
        remaining_33_weeks_total = remaining_rate * 33
        
        total_smp = first_6_weeks_total + remaining_33_weeks_total
        
        # Calculate recoverable amount
        recovery_rate = SMALL_EMPLOYER_RECOVERY_RATE if is_small_employer else STANDARD_RECOVERY_RATE
        recoverable_amount = total_smp * recovery_rate
        
        return {
            "eligible": True,
            "payment_type": "smp",
            "expected_week_of_childbirth": expected_week_of_childbirth.isoformat(),
            "qualifying_week": qualifying_week.isoformat(),
            "maternity_start_date": maternity_start_date.isoformat(),
            "average_weekly_earnings": round(awe, 2),
            "first_6_weeks": {
                "rate": round(first_6_weeks_rate, 2),
                "weeks": 6,
                "total": round(first_6_weeks_total, 2)
            },
            "remaining_33_weeks": {
                "rate": round(remaining_rate, 2),
                "weeks": 33,
                "total": round(remaining_33_weeks_total, 2)
            },
            "total_smp": round(total_smp, 2),
            "total_weeks": 39,
            "recovery_rate": recovery_rate,
            "recoverable_amount": round(recoverable_amount, 2),
            "is_small_employer": is_small_employer
        }
    
    # ==================== SPP CALCULATIONS ====================
    
    async def calculate_spp(
        self,
        employee_id: str,
        company_id: str,
        birth_date: date,
        paternity_weeks: int = 2
    ) -> Dict[str, Any]:
        """
        Calculate Statutory Paternity Pay.
        
        SPP is paid for 1 or 2 weeks at £184.03 or 90% of AWE if lower.
        """
        if paternity_weeks not in [1, 2]:
            paternity_weeks = 2
        
        awe = await self._calculate_average_weekly_earnings(employee_id, company_id)
        
        if awe < LOWER_EARNINGS_LIMIT:
            return {
                "eligible": False,
                "reason": f"Average weekly earnings (£{awe:.2f}) below lower earnings limit (£{LOWER_EARNINGS_LIMIT})"
            }
        
        weekly_rate = min(SPP_WEEKLY_RATE, awe * 0.90)
        total_spp = weekly_rate * paternity_weeks
        
        return {
            "eligible": True,
            "payment_type": "spp",
            "birth_date": birth_date.isoformat(),
            "average_weekly_earnings": round(awe, 2),
            "weekly_rate": round(weekly_rate, 2),
            "weeks": paternity_weeks,
            "total_spp": round(total_spp, 2)
        }
    
    # ==================== RECORD MANAGEMENT ====================
    
    async def create_statutory_payment(
        self,
        employee_id: str,
        company_id: str,
        payment_type: str,
        start_date: date,
        end_date: Optional[date],
        calculation: dict,
        created_by: str,
        notes: Optional[str] = None
    ) -> StatutoryPayment:
        """Create a statutory payment record"""
        # Get company settings for recovery rate
        company = await db.companies.find_one(
            {"company_id": company_id},
            {"small_employer_relief": 1, "_id": 0}
        )
        is_small_employer = company.get("small_employer_relief", False) if company else False
        recovery_rate = SMALL_EMPLOYER_RECOVERY_RATE if is_small_employer else STANDARD_RECOVERY_RATE
        
        # Calculate recoverable amount
        total_amount = calculation.get("total_ssp_amount") or calculation.get("total_smp") or calculation.get("total_spp") or 0
        recoverable = total_amount * recovery_rate
        
        payment = StatutoryPayment(
            payment_id=f"stat_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            payment_type=StatutoryPaymentType(payment_type),
            start_date=start_date,
            end_date=end_date,
            qualifying_week=date.fromisoformat(calculation.get("qualifying_week")) if calculation.get("qualifying_week") else None,
            average_weekly_earnings=calculation.get("average_weekly_earnings", 0),
            weeks_paid=0,
            weeks_remaining=calculation.get("total_weeks") or calculation.get("weeks") or calculation.get("weeks_of_ssp") or 0,
            amount_paid=0,
            amount_recoverable=recoverable,
            recovery_rate=recovery_rate,
            status=PaymentStatus.APPROVED,
            notes=notes,
            created_by=created_by
        )
        
        await db.statutory_payments.insert_one(payment.to_dict())
        
        return payment
    
    async def get_employee_statutory_payments(
        self,
        employee_id: str,
        company_id: str
    ) -> List[dict]:
        """Get all statutory payments for an employee"""
        payments = await db.statutory_payments.find(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return payments
    
    async def get_active_statutory_payments(
        self,
        company_id: str
    ) -> List[dict]:
        """Get all active statutory payments for a company"""
        payments = await db.statutory_payments.find(
            {
                "company_id": company_id,
                "status": {"$in": [PaymentStatus.APPROVED.value, PaymentStatus.IN_PROGRESS.value]}
            },
            {"_id": 0}
        ).to_list(1000)
        
        # Enrich with employee names
        for payment in payments:
            emp = await db.employees.find_one(
                {"employee_id": payment["employee_id"]},
                {"first_name": 1, "last_name": 1, "_id": 0}
            )
            if emp:
                payment["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        
        return payments
    
    async def get_eps_recovery_summary(
        self,
        company_id: str,
        tax_month: int,
        tax_year: str
    ) -> Dict[str, Any]:
        """
        Get statutory payment recovery amounts for EPS submission.
        
        Groups by payment type and sums recoverable amounts not yet claimed.
        """
        payments = await db.statutory_payments.find(
            {
                "company_id": company_id,
                "recovery_claimed": False,
                "amount_paid": {"$gt": 0}
            },
            {"_id": 0}
        ).to_list(1000)
        
        recovery = {
            "smp_recovered": 0,
            "spp_recovered": 0,
            "sap_recovered": 0,
            "shpp_recovered": 0,
            "ssp_recovered": 0,  # SSP is not recoverable but tracked
            "nic_compensation": 0,  # NIC compensation for statutory payments
            "total_recovery": 0
        }
        
        for payment in payments:
            payment_type = payment.get("payment_type")
            recoverable = payment.get("amount_recoverable", 0)
            
            if payment_type == "smp":
                recovery["smp_recovered"] += recoverable
            elif payment_type == "spp":
                recovery["spp_recovered"] += recoverable
            elif payment_type == "sap":
                recovery["sap_recovered"] += recoverable
            elif payment_type == "shpp":
                recovery["shpp_recovered"] += recoverable
        
        recovery["total_recovery"] = (
            recovery["smp_recovered"] + 
            recovery["spp_recovered"] + 
            recovery["sap_recovered"] + 
            recovery["shpp_recovered"]
        )
        
        return {
            "tax_month": tax_month,
            "tax_year": tax_year,
            "recovery": recovery,
            "payment_count": len(payments)
        }
    
    async def _calculate_average_weekly_earnings(
        self,
        employee_id: str,
        company_id: str
    ) -> float:
        """
        Calculate average weekly earnings for statutory payment eligibility.
        
        Uses the 8-week reference period ending with the last normal payday.
        """
        # Get recent payslips
        payslips = await db.payslips.find(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0, "gross_pay": 1, "period": 1}
        ).sort("period", -1).limit(8).to_list(8)
        
        if not payslips:
            # Fallback to employee salary
            employee = await db.employees.find_one(
                {"employee_id": employee_id},
                {"salary": 1, "_id": 0}
            )
            if employee and employee.get("salary"):
                # Assume annual salary, convert to weekly
                return employee["salary"] / 52
            return 0
        
        # Calculate average
        total_gross = sum(p.get("gross_pay", 0) for p in payslips)
        weeks = len(payslips) * 4  # Assuming monthly payslips = 4 weeks each
        
        if weeks > 0:
            return total_gross / (weeks / 4)  # Return weekly
        
        return 0


# Singleton instance
statutory_service = StatutoryPaymentsService()
