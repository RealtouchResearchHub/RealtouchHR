"""
RealtouchHR - Employee Offboarding Service
Handles the full termination workflow:
- Mark employee as leaver
- Generate P45
- Queue leaver for next FPS submission
- Trigger UKVI report for sponsored workers
- Close pension enrolment
- Send final-pay summary
"""
import os
import uuid
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

logger = logging.getLogger(__name__)


TERMINATION_REASONS = [
    {"id": "resignation", "label": "Resignation", "triggers_p45": True},
    {"id": "dismissal", "label": "Dismissal", "triggers_p45": True},
    {"id": "redundancy", "label": "Redundancy", "triggers_p45": True, "may_include_redundancy_pay": True},
    {"id": "retirement", "label": "Retirement", "triggers_p45": True},
    {"id": "end_of_contract", "label": "End of fixed-term contract", "triggers_p45": True},
    {"id": "tupe_transfer", "label": "TUPE transfer", "triggers_p45": False},
    {"id": "death_in_service", "label": "Death in service", "triggers_p45": True},
    {"id": "visa_refusal", "label": "Visa/Work permit refusal", "triggers_p45": True, "ukvi_report": True},
]


class OffboardingService:
    """End-to-end offboarding workflow"""

    async def terminate_employee(
        self,
        employee_id: str,
        company_id: str,
        leaving_date: str,
        reason: str,
        notes: Optional[str],
        redundancy_payment: float,
        holiday_payout_days: float,
        user_id: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """Run the full offboarding pipeline"""
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        now = datetime.now(timezone.utc)
        leaving_dt = date.fromisoformat(leaving_date)

        # 1) Mark as leaver on employee record
        await db.employees.update_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"$set": {
                "status": "terminated",
                "leaving_date": leaving_date,
                "termination_reason": reason,
                "termination_notes": notes,
                "terminated_by": user_id,
                "terminated_at": now.isoformat(),
                "redundancy_payment": redundancy_payment,
                "holiday_payout_days": holiday_payout_days,
                "updated_at": now.isoformat(),
            }}
        )

        # 2) Compute P45 figures from payslips in current tax year
        tax_year_start = self._tax_year_start_for_date(leaving_dt)
        payslips = await db.payslips.find(
            {"employee_id": employee_id},
            {"_id": 0}
        ).to_list(1000)

        # Filter payslips within current tax year via pay_runs
        total_pay = 0.0
        total_tax = 0.0
        total_student_loan = 0.0
        for ps in payslips:
            payrun = await db.pay_runs.find_one({"payrun_id": ps.get("payrun_id")}, {"_id": 0})
            if not payrun:
                continue
            try:
                pay_date = date.fromisoformat(payrun.get("pay_date", ""))
            except (ValueError, TypeError):
                continue
            if pay_date < tax_year_start or pay_date > leaving_dt:
                continue
            total_pay += ps.get("gross_pay", 0) or 0
            total_tax += ps.get("tax_deduction", 0) or 0
            total_student_loan += ps.get("student_loan_deduction", 0) or 0

        p45_data = {
            "leaving_date": leaving_date,
            "tax_code": employee.get("tax_code", ""),
            "week1_month1_basis": False,
            "total_pay_to_date": round(total_pay, 2),
            "total_tax_to_date": round(total_tax, 2),
            "student_loan_deductions": round(total_student_loan, 2),
            "pay_this_employment": round(total_pay, 2),
            "tax_this_employment": round(total_tax, 2),
            "pay_previous_employment": 0.0,
            "tax_previous_employment": 0.0,
        }

        # 3) Persist P45 record
        p45_id = f"p45_{uuid.uuid4().hex[:12]}"
        await db.tax_documents.insert_one({
            "document_id": p45_id,
            "employee_id": employee_id,
            "company_id": company_id,
            "document_type": "p45",
            "tax_year": f"{tax_year_start.year}-{str(tax_year_start.year + 1)[2:]}",
            "data": p45_data,
            "generated_by": user_id,
            "generated_at": now.isoformat(),
        })

        # 4) Queue as leaver on next FPS submission
        await db.rti_leaver_queue.insert_one({
            "queue_id": f"lvr_{uuid.uuid4().hex[:12]}",
            "employee_id": employee_id,
            "company_id": company_id,
            "leaving_date": leaving_date,
            "status": "queued",
            "created_at": now.isoformat(),
        })

        # 5) UKVI report if sponsored worker
        ukvi_report_id = None
        immigration = (employee.get("immigration_status") or {})
        visa_type = immigration.get("visa_type", "")
        is_sponsored = immigration.get("sponsored", False) or visa_type in (
            "skilled_worker", "tier2", "gbm", "scale_up", "intra_company"
        )
        if is_sponsored:
            ukvi_report_id = f"ukvi_{uuid.uuid4().hex[:12]}"
            await db.ukvi_reports.insert_one({
                "report_id": ukvi_report_id,
                "employee_id": employee_id,
                "company_id": company_id,
                "report_type": "worker_ceased_employment",
                "status": "pending_submission",
                "deadline": (leaving_dt + timedelta(days=10)).isoformat(),
                "details": {
                    "reason": reason,
                    "leaving_date": leaving_date,
                    "cos_reference": immigration.get("cos_reference", "")
                },
                "created_at": now.isoformat(),
            })

        # 6) Close pension enrolment (cease contributions)
        pension_closed = False
        existing_enrolment = await db.pension_enrolments.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        if existing_enrolment and existing_enrolment.get("enrolment_status") == "enrolled":
            await db.pension_enrolments.update_one(
                {"employee_id": employee_id, "company_id": company_id},
                {"$set": {
                    "enrolment_status": "ceased",
                    "cessation_date": leaving_date,
                    "cessation_reason": "employment_terminated",
                    "updated_at": now.isoformat(),
                }}
            )
            pension_closed = True

        # 7) Audit log
        await db.audit_log.insert_one({
            "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
            "company_id": company_id,
            "user_id": user_id,
            "user_name": user_name,
            "action": "employee_terminated",
            "entity_type": "employee",
            "entity_id": employee_id,
            "details": {
                "reason": reason,
                "leaving_date": leaving_date,
                "p45_id": p45_id,
                "ukvi_report_id": ukvi_report_id,
                "pension_closed": pension_closed,
            },
            "timestamp": now.isoformat(),
        })

        # 8) Send confirmation email to employee (best-effort)
        try:
            from services.email_service import email_service, get_base_template
            emp_full = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
            subject = f"Leaving confirmation - {employee.get('first_name', '')}"
            html = get_base_template(f"""
                <h2 style="color: #111827; margin: 0 0 16px 0;">Employment End Confirmation</h2>
                <p style="color: #374151; font-size: 16px;">Hi {emp_full},</p>
                <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                    We confirm your last day of employment will be <strong>{leaving_date}</strong>.
                    Your P45 will be available in your self-service portal after your final payroll.
                </p>
                <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                    We wish you all the best in your next steps.
                </p>
            """)
            if employee.get("email"):
                await email_service.send_email(employee["email"], subject, html)
        except Exception as exc:
            logger.warning(f"Offboarding email failed: {exc}")

        return {
            "status": "terminated",
            "employee_id": employee_id,
            "leaving_date": leaving_date,
            "reason": reason,
            "p45_id": p45_id,
            "p45_data": p45_data,
            "ukvi_report_id": ukvi_report_id,
            "pension_closed": pension_closed,
            "queued_for_fps": True,
        }

    async def list_terminations(self, company_id: str) -> List[dict]:
        """List employees marked as terminated"""
        employees = await db.employees.find(
            {"company_id": company_id, "status": "terminated"},
            {"_id": 0}
        ).to_list(1000)
        return employees

    @staticmethod
    def _tax_year_start_for_date(d: date) -> date:
        """UK tax year starts 6 April"""
        start = date(d.year, 4, 6)
        if d < start:
            start = date(d.year - 1, 4, 6)
        return start


offboarding_service = OffboardingService()
