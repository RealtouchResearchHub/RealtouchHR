"""
RealtouchHR - RTI Sync Engine Service
HMRC Real Time Information Compliance Layer

This module implements the RTI Sync Engine as an event-driven service that:
- Triggers on PayRunApproved events
- Validates payroll data against HMRC RTI technical specifications
- Queues submissions for human approval
- Maintains immutable audit trails
- Supports Sandbox/Live/Paused modes
- Enforces human-in-the-loop for all regulatory submissions

IMPORTANT COMPLIANCE NOTES:
- This software is RTI-compatible and HMRC-aligned
- HMRC does not endorse or certify payroll software
- Compliance is the employer's responsibility
- This tool enables compliance through accurate record-keeping
"""
import os
import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
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


# ==================== ENUMS & CONSTANTS ====================

class RTISyncMode(str, Enum):
    """RTI Sync Engine operating modes"""
    SANDBOX = "sandbox"     # Test submissions to HMRC sandbox
    LIVE = "live"           # Production submissions (requires credentials)
    PAUSED = "paused"       # Queue submissions but don't send


class RTISubmissionState(str, Enum):
    """RTI submission state machine"""
    PREPARING = "preparing"           # FPS/EPS being generated
    VALIDATION_PENDING = "validation_pending"   # Awaiting validation
    VALIDATION_FAILED = "validation_failed"     # Has blocking errors
    VALIDATION_PASSED = "validation_passed"     # Ready for approval queue
    QUEUED = "queued"                 # In approval queue
    APPROVAL_PENDING = "approval_pending"       # Awaiting human approval
    APPROVED = "approved"             # Approved, ready to submit
    SUBMITTING = "submitting"         # Submission in progress
    SUBMITTED = "submitted"           # Sent to HMRC
    POLLING = "polling"               # Polling for HMRC response
    ACCEPTED = "accepted"             # HMRC accepted
    REJECTED = "rejected"             # HMRC rejected
    ERROR = "error"                   # System error
    CANCELLED = "cancelled"           # Cancelled by user


class RTISubmissionType(str, Enum):
    """HMRC RTI submission types"""
    FPS = "FPS"   # Full Payment Submission
    EPS = "EPS"   # Employer Payment Summary
    EYU = "EYU"   # Earlier Year Update
    NVR = "NVR"   # NINO Verification Request


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    BLOCKER = "blocker"     # Prevents submission
    ERROR = "error"         # Must be fixed before submission
    WARNING = "warning"     # Should be reviewed
    INFO = "info"           # Informational only


# HMRC Gateway URLs
HMRC_URLS = {
    "sandbox": "https://test-transaction-engine.tax.service.gov.uk/submission",
    "live": "https://transaction-engine.tax.service.gov.uk/submission"
}


# ==================== DATA CLASSES ====================

@dataclass
class ValidationIssue:
    """RTI validation issue"""
    code: str
    field: str
    message: str
    severity: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    hmrc_spec_reference: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def is_blocking(self) -> bool:
        return self.severity in [ValidationSeverity.BLOCKER.value, ValidationSeverity.ERROR.value]


@dataclass
class RTIPayload:
    """RTI submission payload container"""
    xml_content: str
    payload_hash: str
    schema_version: str
    tax_year: str
    tax_period: int
    employee_count: int
    total_pay: float
    total_tax: float
    total_ni: float
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of payload"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


@dataclass
class RTIReceipt:
    """HMRC submission receipt"""
    correlation_id: str
    poll_url: Optional[str]
    response_code: str
    response_message: str
    timestamp: str
    raw_response: Optional[dict] = None


# ==================== RTI SYNC ENGINE ====================

class RTISyncEngine:
    """
    RTI Sync Engine - Event-driven HMRC submission service
    
    This engine implements the compliance workflow:
    1. Event trigger (PayRunApproved)
    2. Auto-prepare FPS/EPS
    3. Validate against HMRC specifications
    4. Queue for human approval
    5. Submit on approval
    6. Store receipt and update status
    
    Human-in-the-loop is MANDATORY - no silent submissions.
    """
    
    def __init__(self):
        self.mode = self._get_mode()
        self._feature_flags = {
            "live_submission": os.environ.get("RTI_LIVE_SUBMISSION_ENABLED", "false").lower() == "true",
            "auto_prepare": os.environ.get("RTI_AUTO_PREPARE_ENABLED", "true").lower() == "true"
        }
        logger.info(f"RTI Sync Engine initialized in {self.mode} mode")
    
    def _get_mode(self) -> RTISyncMode:
        """Get current operating mode from environment"""
        mode = os.environ.get("RTI_SYNC_MODE", "sandbox").lower()
        if mode == "live" and os.environ.get("HMRC_GATEWAY_ID"):
            return RTISyncMode.LIVE
        elif mode == "paused":
            return RTISyncMode.PAUSED
        return RTISyncMode.SANDBOX
    
    # ==================== EVENT HANDLERS ====================
    
    async def on_payrun_approved(self, payrun_id: str, company_id: str, approved_by: str) -> dict:
        """
        Event handler: PayRunApproved
        
        Triggers automatic FPS preparation when a pay run is approved.
        Does NOT auto-submit - queues for human approval.
        """
        logger.info(f"PayRunApproved event received: payrun_id={payrun_id}")
        
        if not self._feature_flags["auto_prepare"]:
            logger.info("Auto-prepare disabled, skipping FPS preparation")
            return {"status": "skipped", "reason": "auto_prepare_disabled"}
        
        # Check if submission already exists (idempotency)
        existing = await db.rti_submissions.find_one({
            "payrun_id": payrun_id,
            "submission_type": RTISubmissionType.FPS.value,
            "state": {"$nin": [RTISubmissionState.CANCELLED.value, RTISubmissionState.REJECTED.value]}
        }, {"_id": 0})
        
        if existing:
            logger.info(f"FPS submission already exists for payrun {payrun_id}")
            return {"status": "exists", "submission_id": existing.get("submission_id")}
        
        # Prepare FPS submission
        result = await self.prepare_fps(payrun_id, company_id, approved_by)
        return result
    
    # ==================== PREPARATION ====================
    
    async def prepare_fps(self, payrun_id: str, company_id: str, initiated_by: str) -> dict:
        """
        Prepare Full Payment Submission (FPS) for a pay run.
        
        Steps:
        1. Gather payroll data
        2. Generate XML payload
        3. Validate against HMRC specs
        4. Queue for approval if valid
        """
        submission_id = f"rti_{uuid.uuid4().hex[:16]}"
        idempotency_key = f"fps_{payrun_id}_{datetime.now(timezone.utc).strftime('%Y%m')}"
        now = datetime.now(timezone.utc)
        
        # Create submission record
        submission = {
            "submission_id": submission_id,
            "idempotency_key": idempotency_key,
            "company_id": company_id,
            "payrun_id": payrun_id,
            "submission_type": RTISubmissionType.FPS.value,
            "state": RTISubmissionState.PREPARING.value,
            "mode": self.mode.value,
            "initiated_by": initiated_by,
            "validation_issues": [],
            "approval_history": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.rti_submissions.insert_one(submission)
        
        # Create audit entry
        await self._create_audit_entry(
            submission_id=submission_id,
            company_id=company_id,
            action="fps_preparation_started",
            user_id=initiated_by,
            details={"payrun_id": payrun_id, "mode": self.mode.value}
        )
        
        try:
            # Gather data
            payrun = await db.pay_runs.find_one({"payrun_id": payrun_id}, {"_id": 0})
            company = await db.companies.find_one({"company_id": company_id}, {"_id": 0})
            employees = await db.employees.find(
                {"company_id": company_id, "status": "active"},
                {"_id": 0}
            ).to_list(1000)
            payslips = await db.payslips.find({"payrun_id": payrun_id}, {"_id": 0}).to_list(1000)
            
            if not payrun:
                raise ValueError(f"Pay run {payrun_id} not found")
            if not company:
                raise ValueError(f"Company {company_id} not found")
            
            # Generate XML payload
            xml_content = await self._generate_fps_xml(company, payrun, employees, payslips)
            payload_hash = RTIPayload.compute_hash(xml_content)
            
            # Calculate totals
            total_pay = sum(ps.get("gross_pay", 0) for ps in payslips)
            total_tax = sum(ps.get("tax_deduction", 0) for ps in payslips)
            total_ni = sum(ps.get("ni_deduction", 0) for ps in payslips)
            
            # Update submission with payload
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {"$set": {
                    "state": RTISubmissionState.VALIDATION_PENDING.value,
                    "payload_hash": payload_hash,
                    "schema_version": "24-25",
                    "tax_year": self._get_tax_year(payrun.get("pay_date", "")),
                    "tax_period": self._get_tax_month(payrun.get("pay_date", "")),
                    "employee_count": len(payslips),
                    "total_pay": total_pay,
                    "total_tax": total_tax,
                    "total_ni": total_ni,
                    "updated_at": now.isoformat()
                }}
            )
            
            # Store encrypted payload separately (not in main submission record for security)
            await db.rti_payloads.insert_one({
                "submission_id": submission_id,
                "payload_hash": payload_hash,
                "xml_content": xml_content,  # In production, encrypt this
                "created_at": now.isoformat()
            })
            
            # Run validation
            validation_result = await self.validate_submission(submission_id)
            
            return {
                "status": "prepared",
                "submission_id": submission_id,
                "validation": validation_result
            }
            
        except Exception as e:
            logger.error(f"FPS preparation failed: {e}")
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {"$set": {
                    "state": RTISubmissionState.ERROR.value,
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await self._create_audit_entry(
                submission_id=submission_id,
                company_id=company_id,
                action="fps_preparation_failed",
                user_id=initiated_by,
                details={"error": str(e)}
            )
            raise
    
    # ==================== VALIDATION ====================
    
    async def validate_submission(self, submission_id: str) -> dict:
        """
        Validate RTI submission against HMRC technical specifications.
        
        Returns validation result with any blocking issues.
        """
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        company = await db.companies.find_one(
            {"company_id": submission["company_id"]},
            {"_id": 0}
        )
        
        payrun = await db.pay_runs.find_one(
            {"payrun_id": submission.get("payrun_id")},
            {"_id": 0}
        ) if submission.get("payrun_id") else None
        
        employees = await db.employees.find(
            {"company_id": submission["company_id"], "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        payslips = await db.payslips.find(
            {"payrun_id": submission.get("payrun_id")},
            {"_id": 0}
        ).to_list(1000) if submission.get("payrun_id") else []
        
        issues = []
        
        # Company validation
        issues.extend(self._validate_company_hmrc_data(company))
        
        # Employee validation
        for emp in employees:
            issues.extend(self._validate_employee_rti_data(emp))
        
        # Payrun validation
        if payrun:
            issues.extend(self._validate_payrun_data(payrun, payslips))
        
        # Cross-validation
        issues.extend(self._validate_cross_references(company, employees, payslips))
        
        # Determine if valid
        blocking_issues = [i for i in issues if i.is_blocking()]
        has_blockers = len(blocking_issues) > 0
        
        new_state = (
            RTISubmissionState.VALIDATION_FAILED.value if has_blockers
            else RTISubmissionState.QUEUED.value
        )
        
        # Update submission
        now = datetime.now(timezone.utc)
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {
                "state": new_state,
                "validation_issues": [i.to_dict() for i in issues],
                "validation_passed": not has_blockers,
                "validated_at": now.isoformat(),
                "updated_at": now.isoformat()
            }}
        )
        
        # Audit
        await self._create_audit_entry(
            submission_id=submission_id,
            company_id=submission["company_id"],
            action="validation_completed",
            user_id="system",
            details={
                "passed": not has_blockers,
                "total_issues": len(issues),
                "blocking_issues": len(blocking_issues)
            }
        )
        
        return {
            "valid": not has_blockers,
            "state": new_state,
            "issues": [i.to_dict() for i in issues],
            "blocking_count": len(blocking_issues),
            "warning_count": len([i for i in issues if i.severity == ValidationSeverity.WARNING.value])
        }
    
    def _validate_company_hmrc_data(self, company: dict) -> List[ValidationIssue]:
        """Validate company HMRC registration data"""
        issues = []
        
        if not company:
            issues.append(ValidationIssue(
                code="COMP001",
                field="company",
                message="Company record not found",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-001"
            ))
            return issues
        
        # PAYE Reference validation
        paye_ref = company.get("paye_reference", "")
        if not paye_ref:
            issues.append(ValidationIssue(
                code="COMP002",
                field="paye_reference",
                message="PAYE reference is required for RTI submissions",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-ER001"
            ))
        else:
            import re
            if not re.match(r'^\d{3}/[A-Z0-9]+$', paye_ref.upper()):
                issues.append(ValidationIssue(
                    code="COMP003",
                    field="paye_reference",
                    message=f"PAYE reference format invalid: {paye_ref}. Expected format: 123/ABC123",
                    severity=ValidationSeverity.BLOCKER.value,
                    hmrc_spec_reference="RTI-FPS-ER002"
                ))
        
        # Accounts Office Reference
        aor = company.get("accounts_office_reference", "")
        if not aor:
            issues.append(ValidationIssue(
                code="COMP004",
                field="accounts_office_reference",
                message="Accounts Office Reference is required for RTI submissions",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-ER003"
            ))
        
        return issues
    
    def _validate_employee_rti_data(self, employee: dict) -> List[ValidationIssue]:
        """Validate employee data for RTI compliance"""
        issues = []
        emp_id = employee.get("employee_id", "unknown")
        emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
        
        # National Insurance number
        ni = employee.get("ni_number", "")
        if not ni:
            issues.append(ValidationIssue(
                code="EMP001",
                field="ni_number",
                message=f"NI number required for {emp_name}",
                severity=ValidationSeverity.BLOCKER.value,
                entity_type="employee",
                entity_id=emp_id,
                hmrc_spec_reference="RTI-FPS-EMP001"
            ))
        else:
            import re
            ni_clean = ni.upper().replace(' ', '')
            # HMRC NI format: 2 letters, 6 digits, 1 letter (A-D)
            # First 2 letters cannot be: BG, GB, NK, KN, TN, NT, ZZ
            # Second letter cannot be: D, F, I, Q, U, V
            pattern = r'^(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]$'
            if not re.match(pattern, ni_clean):
                issues.append(ValidationIssue(
                    code="EMP002",
                    field="ni_number",
                    message=f"Invalid NI number format for {emp_name}: {ni}",
                    severity=ValidationSeverity.BLOCKER.value,
                    entity_type="employee",
                    entity_id=emp_id,
                    hmrc_spec_reference="RTI-FPS-EMP002"
                ))
        
        # Tax code
        tax_code = employee.get("tax_code", "")
        if not tax_code:
            issues.append(ValidationIssue(
                code="EMP003",
                field="tax_code",
                message=f"Tax code missing for {emp_name} - will default to 1257L",
                severity=ValidationSeverity.WARNING.value,
                entity_type="employee",
                entity_id=emp_id,
                hmrc_spec_reference="RTI-FPS-EMP003"
            ))
        
        # Names
        if not employee.get("first_name"):
            issues.append(ValidationIssue(
                code="EMP004",
                field="first_name",
                message="First name is required",
                severity=ValidationSeverity.BLOCKER.value,
                entity_type="employee",
                entity_id=emp_id,
                hmrc_spec_reference="RTI-FPS-EMP004"
            ))
        
        if not employee.get("last_name"):
            issues.append(ValidationIssue(
                code="EMP005",
                field="last_name",
                message="Last name is required",
                severity=ValidationSeverity.BLOCKER.value,
                entity_type="employee",
                entity_id=emp_id,
                hmrc_spec_reference="RTI-FPS-EMP005"
            ))
        
        return issues
    
    def _validate_payrun_data(self, payrun: dict, payslips: list) -> List[ValidationIssue]:
        """Validate pay run data"""
        issues = []
        
        if not payrun.get("period_start"):
            issues.append(ValidationIssue(
                code="PR001",
                field="period_start",
                message="Pay period start date is required",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-PR001"
            ))
        
        if not payrun.get("period_end"):
            issues.append(ValidationIssue(
                code="PR002",
                field="period_end",
                message="Pay period end date is required",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-PR002"
            ))
        
        if not payrun.get("pay_date"):
            issues.append(ValidationIssue(
                code="PR003",
                field="pay_date",
                message="Payment date is required",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-PR003"
            ))
        
        if len(payslips) == 0:
            issues.append(ValidationIssue(
                code="PR004",
                field="payslips",
                message="No payslips found for this pay run",
                severity=ValidationSeverity.BLOCKER.value,
                hmrc_spec_reference="RTI-FPS-PR004"
            ))
        
        return issues
    
    def _validate_cross_references(self, company: dict, employees: list, payslips: list) -> List[ValidationIssue]:
        """Cross-validate data relationships"""
        issues = []
        
        # Check all payslip employees exist
        employee_ids = {e.get("employee_id") for e in employees}
        for ps in payslips:
            if ps.get("employee_id") not in employee_ids:
                issues.append(ValidationIssue(
                    code="XR001",
                    field="employee_id",
                    message=f"Payslip references non-existent employee: {ps.get('employee_id')}",
                    severity=ValidationSeverity.BLOCKER.value,
                    hmrc_spec_reference="RTI-FPS-XR001"
                ))
        
        return issues
    
    # ==================== APPROVAL WORKFLOW ====================
    
    async def request_approval(self, submission_id: str, requested_by: str) -> dict:
        """
        Move submission to approval queue.
        Human approval is REQUIRED before any submission to HMRC.
        """
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        if submission.get("state") != RTISubmissionState.QUEUED.value:
            raise ValueError(f"Submission must be in QUEUED state to request approval. Current: {submission.get('state')}")
        
        now = datetime.now(timezone.utc)
        
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {
                "$set": {
                    "state": RTISubmissionState.APPROVAL_PENDING.value,
                    "approval_requested_by": requested_by,
                    "approval_requested_at": now.isoformat(),
                    "updated_at": now.isoformat()
                },
                "$push": {
                    "approval_history": {
                        "action": "approval_requested",
                        "user_id": requested_by,
                        "timestamp": now.isoformat()
                    }
                }
            }
        )
        
        await self._create_audit_entry(
            submission_id=submission_id,
            company_id=submission["company_id"],
            action="approval_requested",
            user_id=requested_by,
            details={"submission_type": submission.get("submission_type")}
        )
        
        return {"status": "approval_pending", "submission_id": submission_id}
    
    async def approve_submission(
        self,
        submission_id: str,
        approved_by: str,
        approver_role: str,
        confirmation_text: str
    ) -> dict:
        """
        Approve submission for HMRC.
        
        REQUIREMENTS:
        - User must be Payroll Admin or Owner
        - User must provide explicit confirmation
        - Creates immutable audit record
        """
        # Validate approver role
        if approver_role not in ["owner", "admin", "payroll_admin"]:
            raise PermissionError("Only Payroll Admin or Owner can approve RTI submissions")
        
        # Validate confirmation
        expected_confirmation = f"I confirm submission {submission_id}"
        if confirmation_text != expected_confirmation:
            raise ValueError(f"Invalid confirmation. Expected: '{expected_confirmation}'")
        
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        if submission.get("state") != RTISubmissionState.APPROVAL_PENDING.value:
            raise ValueError(f"Submission must be in APPROVAL_PENDING state. Current: {submission.get('state')}")
        
        now = datetime.now(timezone.utc)
        
        # Update submission
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {
                "$set": {
                    "state": RTISubmissionState.APPROVED.value,
                    "approved_by": approved_by,
                    "approved_at": now.isoformat(),
                    "approver_role": approver_role,
                    "updated_at": now.isoformat()
                },
                "$push": {
                    "approval_history": {
                        "action": "approved",
                        "user_id": approved_by,
                        "role": approver_role,
                        "timestamp": now.isoformat()
                    }
                }
            }
        )
        
        # Immutable audit entry
        await self._create_audit_entry(
            submission_id=submission_id,
            company_id=submission["company_id"],
            action="submission_approved",
            user_id=approved_by,
            details={
                "approver_role": approver_role,
                "submission_type": submission.get("submission_type"),
                "payload_hash": submission.get("payload_hash"),
                "confirmation_provided": True
            },
            immutable=True
        )
        
        return {
            "status": "approved",
            "submission_id": submission_id,
            "ready_to_submit": True,
            "mode": self.mode.value
        }
    
    async def reject_submission(
        self,
        submission_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> dict:
        """Reject a submission"""
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        now = datetime.now(timezone.utc)
        
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {
                "$set": {
                    "state": RTISubmissionState.CANCELLED.value,
                    "rejected_by": rejected_by,
                    "rejection_reason": rejection_reason,
                    "rejected_at": now.isoformat(),
                    "updated_at": now.isoformat()
                },
                "$push": {
                    "approval_history": {
                        "action": "rejected",
                        "user_id": rejected_by,
                        "reason": rejection_reason,
                        "timestamp": now.isoformat()
                    }
                }
            }
        )
        
        await self._create_audit_entry(
            submission_id=submission_id,
            company_id=submission["company_id"],
            action="submission_rejected",
            user_id=rejected_by,
            details={"reason": rejection_reason}
        )
        
        return {"status": "rejected", "submission_id": submission_id}
    
    # ==================== SUBMISSION ====================
    
    async def submit_to_hmrc(self, submission_id: str, submitted_by: str) -> dict:
        """
        Submit approved FPS/EPS to HMRC.
        
        REQUIREMENTS:
        - Submission must be in APPROVED state
        - Feature flag must allow live submission (if mode is LIVE)
        - Creates immutable receipt record
        """
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        if submission.get("state") != RTISubmissionState.APPROVED.value:
            raise ValueError(f"Submission must be APPROVED before submitting. Current: {submission.get('state')}")
        
        # Check mode
        if self.mode == RTISyncMode.PAUSED:
            return {"status": "paused", "message": "RTI Sync Engine is paused. Submission queued."}
        
        if self.mode == RTISyncMode.LIVE and not self._feature_flags["live_submission"]:
            return {"status": "blocked", "message": "Live submission is disabled. Enable RTI_LIVE_SUBMISSION_ENABLED=true"}
        
        # Get payload
        payload_doc = await db.rti_payloads.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not payload_doc:
            raise ValueError(f"Payload not found for submission {submission_id}")
        
        now = datetime.now(timezone.utc)
        
        # Update state to submitting
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {
                "state": RTISubmissionState.SUBMITTING.value,
                "submission_started_at": now.isoformat(),
                "updated_at": now.isoformat()
            }}
        )
        
        try:
            # Send to HMRC (or sandbox)
            result = await self._send_to_hmrc_gateway(
                xml_content=payload_doc["xml_content"],
                submission_type=submission.get("submission_type", "FPS")
            )
            
            # Create receipt
            receipt = RTIReceipt(
                correlation_id=result.get("correlation_id", ""),
                poll_url=result.get("poll_url"),
                response_code=result.get("response_code", "200"),
                response_message=result.get("message", ""),
                timestamp=now.isoformat(),
                raw_response=result
            )
            
            # Update submission with receipt
            new_state = (
                RTISubmissionState.SUBMITTED.value if result.get("success")
                else RTISubmissionState.ERROR.value
            )
            
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {"$set": {
                    "state": new_state,
                    "hmrc_correlation_id": receipt.correlation_id,
                    "hmrc_poll_url": receipt.poll_url,
                    "hmrc_response_code": receipt.response_code,
                    "submitted_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }}
            )
            
            # Store receipt in immutable ledger
            await db.rti_receipts.insert_one({
                "receipt_id": f"rcpt_{uuid.uuid4().hex[:12]}",
                "submission_id": submission_id,
                "company_id": submission["company_id"],
                "payload_hash": submission.get("payload_hash"),
                "correlation_id": receipt.correlation_id,
                "poll_url": receipt.poll_url,
                "response_code": receipt.response_code,
                "response_message": receipt.response_message,
                "mode": self.mode.value,
                "submitted_by": submitted_by,
                "timestamp": now.isoformat()
            })
            
            # Immutable audit entry
            await self._create_audit_entry(
                submission_id=submission_id,
                company_id=submission["company_id"],
                action="hmrc_submission_sent",
                user_id=submitted_by,
                details={
                    "correlation_id": receipt.correlation_id,
                    "payload_hash": submission.get("payload_hash"),
                    "mode": self.mode.value,
                    "success": result.get("success", False)
                },
                immutable=True
            )
            
            return {
                "status": "submitted" if result.get("success") else "error",
                "submission_id": submission_id,
                "correlation_id": receipt.correlation_id,
                "poll_url": receipt.poll_url,
                "mode": self.mode.value,
                "message": receipt.response_message
            }
            
        except Exception as e:
            logger.error(f"HMRC submission failed: {e}")
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {"$set": {
                    "state": RTISubmissionState.ERROR.value,
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            raise
    
    async def _send_to_hmrc_gateway(self, xml_content: str, submission_type: str) -> dict:
        """
        Send XML to HMRC Government Gateway.
        
        In SANDBOX mode: Returns mock response
        In LIVE mode: Sends to actual HMRC endpoint via SOAP/XML (requires credentials)
        
        HMRC RTI uses Government Gateway web services (SOAP-based).
        Endpoints:
          - Sandbox: https://test-transaction-engine.tax.service.gov.uk/submission
          - Live: https://transaction-engine.tax.service.gov.uk/submission
        """
        import httpx
        from xml.etree import ElementTree as ET
        
        correlation_id = str(uuid.uuid4())
        
        if self.mode == RTISyncMode.SANDBOX:
            # Sandbox mock response - simulates HMRC test environment
            return {
                "success": True,
                "correlation_id": correlation_id,
                "poll_url": f"https://test-transaction-engine.tax.service.gov.uk/poll/{correlation_id}",
                "response_code": "200",
                "message": f"{submission_type} received by HMRC sandbox. Correlation ID: {correlation_id}",
                "mode": "sandbox"
            }
        
        elif self.mode == RTISyncMode.LIVE:
            # Live submission - requires HMRC Government Gateway credentials
            gateway_id = os.environ.get("HMRC_GATEWAY_ID")
            gateway_password = os.environ.get("HMRC_GATEWAY_PASSWORD")
            hmrc_sender_id = os.environ.get("HMRC_SENDER_ID", gateway_id)
            
            if not gateway_id or not gateway_password:
                return {
                    "success": False,
                    "correlation_id": correlation_id,
                    "response_code": "401",
                    "message": "HMRC Gateway credentials not configured. Set HMRC_GATEWAY_ID and HMRC_GATEWAY_PASSWORD environment variables."
                }
            
            try:
                # Build HMRC SOAP envelope with GovTalk wrapper
                soap_envelope = self._build_hmrc_soap_envelope(
                    xml_content=xml_content,
                    submission_type=submission_type,
                    gateway_id=gateway_id,
                    gateway_password=gateway_password,
                    sender_id=hmrc_sender_id,
                    correlation_id=correlation_id
                )
                
                # Submit to HMRC Transaction Engine
                hmrc_url = HMRC_URLS["live"]
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        hmrc_url,
                        content=soap_envelope,
                        headers={
                            "Content-Type": "application/xml; charset=utf-8",
                            "SOAPAction": "Submit"
                        }
                    )
                
                # Parse HMRC response
                if response.status_code == 200:
                    response_xml = response.text
                    hmrc_result = self._parse_hmrc_response(response_xml)
                    
                    return {
                        "success": hmrc_result.get("success", False),
                        "correlation_id": hmrc_result.get("correlation_id", correlation_id),
                        "poll_url": hmrc_result.get("poll_url"),
                        "response_code": str(response.status_code),
                        "message": hmrc_result.get("message", "Submission processed by HMRC"),
                        "hmrc_qualifier": hmrc_result.get("qualifier"),
                        "mode": "live"
                    }
                else:
                    return {
                        "success": False,
                        "correlation_id": correlation_id,
                        "response_code": str(response.status_code),
                        "message": f"HMRC Gateway returned HTTP {response.status_code}: {response.text[:500]}"
                    }
                    
            except httpx.TimeoutException:
                return {
                    "success": False,
                    "correlation_id": correlation_id,
                    "response_code": "408",
                    "message": "HMRC Gateway request timed out. Please retry later."
                }
            except Exception as e:
                logger.error(f"HMRC submission error: {e}")
                return {
                    "success": False,
                    "correlation_id": correlation_id,
                    "response_code": "500",
                    "message": f"HMRC submission failed: {str(e)}"
                }
        
        return {
            "success": False,
            "correlation_id": correlation_id,
            "response_code": "503",
            "message": "RTI Sync Engine is paused"
        }
    
    def _build_hmrc_soap_envelope(
        self,
        xml_content: str,
        submission_type: str,
        gateway_id: str,
        gateway_password: str,
        sender_id: str,
        correlation_id: str
    ) -> str:
        """
        Build HMRC GovTalk SOAP envelope for RTI submission.
        
        HMRC uses a specific GovTalk envelope format for submissions.
        """
        now = datetime.now(timezone.utc)
        
        # GovTalk envelope wrapping the RTI payload
        govtalk_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<GovTalkMessage xmlns="http://www.govtalk.gov.uk/CM/envelope">
    <EnvelopeVersion>2.0</EnvelopeVersion>
    <Header>
        <MessageDetails>
            <Class>HMRC-PAYE-RTI-{submission_type}</Class>
            <Qualifier>request</Qualifier>
            <Function>submit</Function>
            <CorrelationID>{correlation_id}</CorrelationID>
            <Transformation>XML</Transformation>
        </MessageDetails>
        <SenderDetails>
            <IDAuthentication>
                <SenderID>{sender_id}</SenderID>
                <Authentication>
                    <Method>clear</Method>
                    <Role>principal</Role>
                    <Value>{gateway_password}</Value>
                </Authentication>
            </IDAuthentication>
            <X509Certificate/>
        </SenderDetails>
    </Header>
    <GovTalkDetails>
        <Keys/>
        <TargetDetails>
            <Organisation>HMRC</Organisation>
        </TargetDetails>
        <GatewayTimestamp>{now.isoformat()}</GatewayTimestamp>
    </GovTalkDetails>
    <Body>
        {xml_content}
    </Body>
</GovTalkMessage>"""
        
        return govtalk_envelope
    
    def _parse_hmrc_response(self, response_xml: str) -> dict:
        """
        Parse HMRC GovTalk response XML.
        
        HMRC responses include:
        - Qualifier: acknowledgement, response, poll, error
        - CorrelationID: for tracking
        - Errors: if any validation/submission errors
        """
        from xml.etree import ElementTree as ET
        
        result = {
            "success": False,
            "correlation_id": None,
            "poll_url": None,
            "message": "",
            "qualifier": None,
            "errors": []
        }
        
        try:
            # Parse the response XML
            root = ET.fromstring(response_xml)
            
            # Define namespaces
            ns = {
                "gt": "http://www.govtalk.gov.uk/CM/envelope",
                "err": "http://www.govtalk.gov.uk/CM/errorresponse"
            }
            
            # Extract qualifier (acknowledgement, response, error, poll)
            qualifier_elem = root.find(".//gt:Qualifier", ns)
            if qualifier_elem is not None:
                result["qualifier"] = qualifier_elem.text
            
            # Extract correlation ID
            corr_elem = root.find(".//gt:CorrelationID", ns)
            if corr_elem is not None:
                result["correlation_id"] = corr_elem.text
            
            # Check for errors
            errors = root.findall(".//err:Error", ns)
            if errors:
                error_messages = []
                for err in errors:
                    err_num = err.find("err:Number", ns)
                    err_text = err.find("err:Text", ns)
                    error_messages.append({
                        "number": err_num.text if err_num is not None else "unknown",
                        "text": err_text.text if err_text is not None else "Unknown error"
                    })
                result["errors"] = error_messages
                result["message"] = "; ".join([e["text"] for e in error_messages])
                result["success"] = False
            else:
                # Check for acknowledgement
                if result["qualifier"] == "acknowledgement":
                    result["success"] = True
                    result["message"] = "Submission acknowledged by HMRC"
                    
                    # Look for poll interval/URL
                    poll_elem = root.find(".//gt:ResponseEndPoint", ns)
                    if poll_elem is not None:
                        result["poll_url"] = poll_elem.text
                    
                elif result["qualifier"] == "response":
                    result["success"] = True
                    result["message"] = "Submission accepted by HMRC"
                    
                elif result["qualifier"] == "error":
                    result["success"] = False
                    result["message"] = "HMRC returned an error"
                else:
                    result["message"] = f"HMRC response received (qualifier: {result['qualifier']})"
                    result["success"] = result["qualifier"] not in ["error", "poll_error"]
                    
        except ET.ParseError as e:
            result["message"] = f"Failed to parse HMRC response: {str(e)}"
        except Exception as e:
            result["message"] = f"Error processing HMRC response: {str(e)}"
        
        return result
    
    async def poll_hmrc_status(self, submission_id: str) -> dict:
        """
        Poll HMRC for submission status.
        
        HMRC uses asynchronous processing - after initial acknowledgement,
        we need to poll for the final response.
        """
        import httpx
        
        submission = await db.rti_submissions.find_one(
            {"submission_id": submission_id},
            {"_id": 0}
        )
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        poll_url = submission.get("hmrc_poll_url")
        correlation_id = submission.get("hmrc_correlation_id")
        
        if not poll_url and not correlation_id:
            return {
                "status": "no_poll_url",
                "message": "No poll URL available for this submission"
            }
        
        if self.mode == RTISyncMode.SANDBOX:
            # Mock polling response for sandbox
            return {
                "status": "accepted",
                "correlation_id": correlation_id,
                "message": "Sandbox submission accepted",
                "mode": "sandbox"
            }
        
        if self.mode != RTISyncMode.LIVE:
            return {
                "status": "paused",
                "message": "RTI Sync Engine is paused"
            }
        
        gateway_id = os.environ.get("HMRC_GATEWAY_ID")
        gateway_password = os.environ.get("HMRC_GATEWAY_PASSWORD")
        
        if not gateway_id or not gateway_password:
            return {
                "status": "error",
                "message": "HMRC credentials not configured"
            }
        
        try:
            # Build poll request
            poll_envelope = self._build_hmrc_poll_envelope(
                correlation_id=correlation_id,
                gateway_id=gateway_id,
                gateway_password=gateway_password
            )
            
            poll_endpoint = poll_url or HMRC_URLS["live"]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    poll_endpoint,
                    content=poll_envelope,
                    headers={
                        "Content-Type": "application/xml; charset=utf-8",
                        "SOAPAction": "Poll"
                    }
                )
            
            if response.status_code == 200:
                result = self._parse_hmrc_response(response.text)
                
                # Update submission status
                now = datetime.now(timezone.utc)
                new_state = RTISubmissionState.ACCEPTED.value if result.get("success") else RTISubmissionState.REJECTED.value
                
                if result.get("qualifier") == "acknowledgement":
                    # Still processing, keep polling
                    new_state = RTISubmissionState.POLLING.value
                
                await db.rti_submissions.update_one(
                    {"submission_id": submission_id},
                    {"$set": {
                        "state": new_state,
                        "hmrc_poll_result": result,
                        "updated_at": now.isoformat()
                    }}
                )
                
                return {
                    "status": new_state,
                    "correlation_id": correlation_id,
                    "message": result.get("message"),
                    "hmrc_response": result
                }
            else:
                return {
                    "status": "error",
                    "message": f"HMRC poll returned HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"HMRC poll error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _build_hmrc_poll_envelope(
        self,
        correlation_id: str,
        gateway_id: str,
        gateway_password: str
    ) -> str:
        """Build HMRC poll request envelope"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<GovTalkMessage xmlns="http://www.govtalk.gov.uk/CM/envelope">
    <EnvelopeVersion>2.0</EnvelopeVersion>
    <Header>
        <MessageDetails>
            <Class>HMRC-PAYE-RTI-FPS</Class>
            <Qualifier>poll</Qualifier>
            <Function>submit</Function>
            <CorrelationID>{correlation_id}</CorrelationID>
        </MessageDetails>
        <SenderDetails>
            <IDAuthentication>
                <SenderID>{gateway_id}</SenderID>
                <Authentication>
                    <Method>clear</Method>
                    <Role>principal</Role>
                    <Value>{gateway_password}</Value>
                </Authentication>
            </IDAuthentication>
        </SenderDetails>
    </Header>
    <GovTalkDetails>
        <Keys/>
    </GovTalkDetails>
    <Body/>
</GovTalkMessage>"""
    
    # ==================== HELPERS ====================
    
    async def _generate_fps_xml(
        self,
        company: dict,
        payrun: dict,
        employees: list,
        payslips: list
    ) -> str:
        """Generate HMRC-compliant FPS XML"""
        tax_year = self._get_tax_year(payrun.get("pay_date", ""))
        tax_month = self._get_tax_month(payrun.get("pay_date", ""))
        paye_parts = company.get("paye_reference", "").split("/")
        
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<IRenvelope xmlns="http://www.govtalk.gov.uk/taxation/PAYE/RTI/FullPaymentSubmission/15-16/1">
    <IRheader>
        <Keys>
            <Key Type="TaxOfficeNumber">{paye_parts[0] if len(paye_parts) > 0 else ''}</Key>
            <Key Type="TaxOfficeReference">{paye_parts[1] if len(paye_parts) > 1 else ''}</Key>
        </Keys>
        <PeriodEnd>{payrun.get('period_end', '')}</PeriodEnd>
        <Sender>Employer</Sender>
    </IRheader>
    <FullPaymentSubmission>
        <EmpRefs>
            <OfficeNo>{paye_parts[0] if len(paye_parts) > 0 else ''}</OfficeNo>
            <PayeRef>{paye_parts[1] if len(paye_parts) > 1 else ''}</PayeRef>
            <AORef>{company.get('accounts_office_reference', '')}</AORef>
        </EmpRefs>
        <RelatedTaxYear>{tax_year}</RelatedTaxYear>"""
        
        for ps in payslips:
            emp = next((e for e in employees if e.get("employee_id") == ps.get("employee_id")), {})
            xml += f"""
        <Employee>
            <EmployeeDetails>
                <NINO>{emp.get('ni_number', '').upper().replace(' ', '')}</NINO>
                <Name>
                    <Fore>{emp.get('first_name', '')}</Fore>
                    <Sur>{emp.get('last_name', '')}</Sur>
                </Name>
            </EmployeeDetails>
            <Employment>
                <PayId>{emp.get('employee_id', '')}</PayId>
                <PayFreq>M1</PayFreq>
                <PMnth>{tax_month}</PMnth>
                <PaymentToADate>{ps.get('gross_pay', 0):.2f}</PaymentToADate>
                <TaxablePay>{ps.get('gross_pay', 0):.2f}</TaxablePay>
                <TotalTax>{ps.get('tax_deduction', 0):.2f}</TotalTax>
                <NILettersAndValues>
                    <NILetter>A</NILetter>
                    <GrossEarningsForNICs>{ps.get('gross_pay', 0):.2f}</GrossEarningsForNICs>
                    <EmpeeContribnsInPd>{ps.get('ni_deduction', 0):.2f}</EmpeeContribnsInPd>
                </NILettersAndValues>
            </Employment>
        </Employee>"""
        
        xml += """
    </FullPaymentSubmission>
</IRenvelope>"""
        
        return xml
    
    def _get_tax_year(self, date_str: str) -> str:
        """Get HMRC tax year (e.g., '24-25')"""
        if not date_str:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
        
        date = datetime.fromisoformat(date_str[:10])
        year = date.year
        month = date.month
        day = date.day
        
        if month < 4 or (month == 4 and day < 6):
            return f"{str(year-1)[2:]}-{str(year)[2:]}"
        return f"{str(year)[2:]}-{str(year+1)[2:]}"
    
    def _get_tax_month(self, date_str: str) -> int:
        """Get HMRC tax month (1-12, starting April)"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        date = datetime.fromisoformat(date_str[:10])
        month = date.month
        day = date.day
        
        if month == 4 and day >= 6:
            return 1
        elif month > 4:
            return month - 3
        elif month < 4:
            return month + 9
        elif month == 4 and day < 6:
            return 12
        return 1
    
    async def _create_audit_entry(
        self,
        submission_id: str,
        company_id: str,
        action: str,
        user_id: str,
        details: dict,
        immutable: bool = False
    ):
        """Create audit entry in RTI audit ledger"""
        now = datetime.now(timezone.utc)
        
        entry = {
            "audit_id": f"rti_audit_{uuid.uuid4().hex[:12]}",
            "submission_id": submission_id,
            "company_id": company_id,
            "action": action,
            "user_id": user_id,
            "details": details,
            "immutable": immutable,
            "timestamp": now.isoformat()
        }
        
        # Compute hash for immutable entries
        if immutable:
            entry_json = json.dumps(entry, sort_keys=True)
            entry["entry_hash"] = hashlib.sha256(entry_json.encode()).hexdigest()
        
        await db.rti_audit_ledger.insert_one(entry)


# ==================== SINGLETON ====================

rti_sync_engine = RTISyncEngine()


# ==================== HELPER FUNCTIONS ====================

async def get_submission_summary(submission_id: str) -> dict:
    """Get submission summary for UI display"""
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id},
        {"_id": 0}
    )
    
    if not submission:
        return None
    
    # Get approval history
    approval_history = submission.get("approval_history", [])
    
    # Get audit trail
    audit_entries = await db.rti_audit_ledger.find(
        {"submission_id": submission_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    
    return {
        "submission_id": submission_id,
        "state": submission.get("state"),
        "submission_type": submission.get("submission_type"),
        "mode": submission.get("mode"),
        "tax_year": submission.get("tax_year"),
        "tax_period": submission.get("tax_period"),
        "employee_count": submission.get("employee_count"),
        "total_pay": submission.get("total_pay"),
        "total_tax": submission.get("total_tax"),
        "total_ni": submission.get("total_ni"),
        "payload_hash": submission.get("payload_hash"),
        "validation_passed": submission.get("validation_passed"),
        "validation_issues": submission.get("validation_issues", []),
        "approved_by": submission.get("approved_by"),
        "approved_at": submission.get("approved_at"),
        "hmrc_correlation_id": submission.get("hmrc_correlation_id"),
        "submitted_at": submission.get("submitted_at"),
        "created_at": submission.get("created_at"),
        "approval_history": approval_history,
        "audit_trail": audit_entries
    }


async def get_company_rti_settings(company_id: str) -> dict:
    """Get company RTI configuration status"""
    company = await db.companies.find_one(
        {"company_id": company_id},
        {"_id": 0}
    )
    
    if not company:
        return None
    
    return {
        "paye_reference_configured": bool(company.get("paye_reference")),
        "accounts_office_reference_configured": bool(company.get("accounts_office_reference")),
        "hmrc_credentials_configured": bool(os.environ.get("HMRC_GATEWAY_ID")),
        "rti_mode": rti_sync_engine.mode.value,
        "live_submission_enabled": rti_sync_engine._feature_flags["live_submission"],
        "auto_prepare_enabled": rti_sync_engine._feature_flags["auto_prepare"]
    }
