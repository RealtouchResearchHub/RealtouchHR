"""
RealtouchHR - HMRC RTI Routes
Full Payment Submission (FPS) and Employer Payment Summary (EPS)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import hashlib
import logging
import os
import sys
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, ConfigDict
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

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "owner"
    company_id: Optional[str] = None
    employee_id: Optional[str] = None
    theme_preference: str = "light"
    created_at: datetime

class RTISubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    submission_id: str
    company_id: str
    payrun_id: Optional[str] = None
    submission_type: str
    status: str
    validation_errors: List[Dict[str, Any]] = []
    validation_warnings: List[Dict[str, Any]] = []
    hmrc_response: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    poll_url: Optional[str] = None
    submitted_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime

class RTISubmissionRequest(BaseModel):
    payrun_id: str
    submission_type: str = "FPS"
    test_mode: bool = True

class HealthCheckIssue(BaseModel):
    severity: str
    category: str
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    title: str
    description: str
    action_required: str

class PayrollHealthCheckResult(BaseModel):
    payrun_id: str
    check_date: str
    overall_status: str
    score: int
    issues: List[HealthCheckIssue]
    can_proceed: bool

class EPSData(BaseModel):
    eps_reason: Optional[str] = None          # e.g. 'no_payment', 'smp_recovery', 'final_submission'
    test_mode: bool = True
    no_payment_period: Optional[str] = None   # e.g. '2026-04'
    no_payment_dates: Optional[List[str]] = None
    period_of_inactivity: Optional[Dict[str, str]] = None
    smp_recovered: float = 0
    spp_recovered: float = 0
    sap_recovered: float = 0
    shpp_recovered: float = 0
    nic_compensation: float = 0
    cis_deductions: float = 0
    employment_allowance: bool = False
    final_submission: bool = False
    cessation_date: Optional[str] = None

# ==================== HELPERS ====================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_submission_id() -> str:
    return f"rti_{uuid.uuid4().hex[:12]}"

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
            if isinstance(user_doc.get("created_at"), str):
                user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)

async def require_payroll(request: Request) -> User:
    """Require payroll admin or above"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "payroll_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


# ==================== RTI VALIDATION ====================

class RTIStatus:
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    POLLING = "polling"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class RTIValidator:
    """Validates payroll data against HMRC RTI rules"""
    
    @staticmethod
    def validate_ni_number(ni: str) -> Optional[Dict]:
        """Validate National Insurance number format"""
        if not ni:
            return {"code": "NI001", "field": "ni_number", "message": "National Insurance number is required", "severity": "error"}
        
        import re
        ni_clean = ni.upper().replace(' ', '')
        pattern = r'^(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$'
        
        if not re.match(pattern, ni_clean):
            return {"code": "NI002", "field": "ni_number", "message": f"Invalid NI number format: {ni}", "severity": "error"}
        return None
    
    @staticmethod
    def validate_tax_code(tax_code: str) -> Optional[Dict]:
        """Validate tax code format"""
        if not tax_code:
            return {"code": "TAX001", "field": "tax_code", "message": "Tax code is required", "severity": "warning"}
        
        import re
        code_clean = tax_code.upper().replace(' ', '')
        pattern = r'^(S)?(\d{1,4}[LMNPTY]|BR|D[01]|NT|0T|K\d+)$'
        
        if not re.match(pattern, code_clean):
            return {"code": "TAX002", "field": "tax_code", "message": f"Invalid tax code format: {tax_code}", "severity": "warning"}
        return None
    
    @staticmethod
    def validate_employee_for_fps(employee: dict) -> List[Dict]:
        """Validate employee data for FPS submission"""
        errors = []
        
        if not employee.get("first_name"):
            errors.append({"code": "EMP001", "field": "first_name", "message": "First name is required", "severity": "error"})
        if not employee.get("last_name"):
            errors.append({"code": "EMP002", "field": "last_name", "message": "Last name is required", "severity": "error"})
        
        ni_error = RTIValidator.validate_ni_number(employee.get("ni_number", ""))
        if ni_error:
            errors.append(ni_error)
        
        tax_error = RTIValidator.validate_tax_code(employee.get("tax_code", ""))
        if tax_error:
            errors.append(tax_error)
        
        salary = employee.get("salary", 0)
        if not salary or salary <= 0:
            errors.append({"code": "EMP003", "field": "salary", "message": "Valid salary is required", "severity": "error"})
        
        return errors
    
    @staticmethod
    def validate_company_for_rti(company: dict) -> List[Dict]:
        """Validate company data for RTI submission"""
        errors = []
        
        import re
        paye_ref = company.get("paye_reference", "")
        if not paye_ref:
            errors.append({"code": "COMP001", "field": "paye_reference", "message": "PAYE reference is required for RTI", "severity": "error"})
        elif not re.match(r'^\d{3}/[A-Z0-9]+$', paye_ref.upper()):
            errors.append({"code": "COMP002", "field": "paye_reference", "message": f"Invalid PAYE reference format: {paye_ref}", "severity": "error"})
        
        aor = company.get("accounts_office_reference", "")
        if not aor:
            errors.append({"code": "COMP003", "field": "accounts_office_reference", "message": "Accounts Office Reference is required for RTI", "severity": "error"})
        
        return errors


class HMRCService:
    """HMRC RTI Submission Service"""
    
    def __init__(self, use_production: bool = False):
        self.use_production = use_production
        self.base_url = "https://transaction-engine.tax.service.gov.uk/submission" if use_production else "https://test-transaction-engine.tax.service.gov.uk/submission"
    
    async def validate_fps(self, company: dict, payrun: dict, employees: list, payslips: list) -> Dict[str, Any]:
        """Validate data for FPS submission"""
        errors = []
        warnings = []
        
        company_errors = RTIValidator.validate_company_for_rti(company)
        for err in company_errors:
            if err.get("severity") == "error":
                errors.append(err)
            else:
                warnings.append(err)
        
        for emp in employees:
            emp_errors = RTIValidator.validate_employee_for_fps(emp)
            for err in emp_errors:
                if err.get("severity") == "error":
                    errors.append(err)
                else:
                    warnings.append(err)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "employee_count": len(employees),
            "total_pay": sum(ps.get("gross_pay", 0) for ps in payslips)
        }
    
    async def submit_to_hmrc(self, xml_content: str, submission_type: str = "FPS") -> Dict[str, Any]:
        """Submit XML to HMRC Gateway (test mode)"""
        correlation_id = str(uuid.uuid4())
        
        if self.use_production:
            return {
                "success": False,
                "error": "Production submission requires HMRC Gateway credentials",
                "correlation_id": correlation_id
            }
        
        return {
            "success": True,
            "correlation_id": correlation_id,
            "poll_url": f"{self.base_url}/poll/{correlation_id}",
            "status": "submitted",
            "message": "Submission received. This is a TEST submission.",
            "timestamp": now_iso()
        }
    
    def get_tax_month(self, date_str: str) -> int:
        """Get HMRC tax month from a date"""
        date = datetime.fromisoformat(date_str)
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
    
    def get_tax_year(self, date_str: str) -> str:
        """Get HMRC tax year from a date"""
        date = datetime.fromisoformat(date_str)
        year = date.year
        month = date.month
        day = date.day
        
        if month < 4 or (month == 4 and day < 6):
            return f"{str(year-1)[2:]}-{str(year)[2:]}"
        return f"{str(year)[2:]}-{str(year+1)[2:]}"
    
    async def generate_fps_xml(self, company: dict, payrun: dict, employees: list, payslips: list, credentials: dict) -> str:
        """Generate FPS XML for HMRC submission (simplified test version)"""
        # In production, this would generate proper HMRC-compliant XML
        # For test mode, we generate a simplified XML structure
        tax_year = self.get_tax_year(payrun.get("pay_date", datetime.now().isoformat()[:10]))
        tax_month = self.get_tax_month(payrun.get("pay_date", datetime.now().isoformat()[:10]))
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<IRenvelope xmlns="http://www.govtalk.gov.uk/taxation/PAYE/RTI/FullPaymentSubmission/15-16/1">
  <IRheader>
    <Keys>
      <Key Type="TaxOfficeNumber">{company.get('paye_reference', '').split('/')[0] if company.get('paye_reference') else ''}</Key>
      <Key Type="TaxOfficeReference">{company.get('paye_reference', '').split('/')[1] if company.get('paye_reference') and '/' in company.get('paye_reference', '') else ''}</Key>
    </Keys>
    <PeriodEnd>{payrun.get('period_end', '')}</PeriodEnd>
    <Sender>Employer</Sender>
  </IRheader>
  <FullPaymentSubmission>
    <EmpRefs>
      <OfficeNo>{company.get('paye_reference', '').split('/')[0] if company.get('paye_reference') else ''}</OfficeNo>
      <PayeRef>{company.get('paye_reference', '').split('/')[1] if company.get('paye_reference') and '/' in company.get('paye_reference', '') else ''}</PayeRef>
      <AORef>{company.get('accounts_office_reference', '')}</AORef>
    </EmpRefs>
    <RelatedTaxYear>{tax_year}</RelatedTaxYear>"""
        
        for i, ps in enumerate(payslips):
            emp = next((e for e in employees if e.get("employee_id") == ps.get("employee_id")), {})
            xml_content += f"""
    <Employee>
      <EmployeeDetails>
        <NINO>{emp.get('ni_number', '')}</NINO>
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
        
        xml_content += """
  </FullPaymentSubmission>
</IRenvelope>"""
        
        return xml_content
    
    async def generate_eps_xml(self, company: dict, tax_month: int, tax_year: str, eps_data: dict, credentials: dict) -> str:
        """Generate EPS XML for HMRC submission (simplified test version)"""
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<IRenvelope xmlns="http://www.govtalk.gov.uk/taxation/PAYE/RTI/EmployerPaymentSummary/15-16/1">
  <IRheader>
    <Keys>
      <Key Type="TaxOfficeNumber">{company.get('paye_reference', '').split('/')[0] if company.get('paye_reference') else ''}</Key>
      <Key Type="TaxOfficeReference">{company.get('paye_reference', '').split('/')[1] if company.get('paye_reference') and '/' in company.get('paye_reference', '') else ''}</Key>
    </Keys>
    <Sender>Employer</Sender>
  </IRheader>
  <EmployerPaymentSummary>
    <EmpRefs>
      <OfficeNo>{company.get('paye_reference', '').split('/')[0] if company.get('paye_reference') else ''}</OfficeNo>
      <PayeRef>{company.get('paye_reference', '').split('/')[1] if company.get('paye_reference') and '/' in company.get('paye_reference', '') else ''}</PayeRef>
      <AORef>{company.get('accounts_office_reference', '')}</AORef>
    </EmpRefs>
    <RelatedTaxYear>{tax_year}</RelatedTaxYear>
    <RecoverableAmountsYTD>
      <SMPRecovered>{eps_data.get('smp_recovered', 0):.2f}</SMPRecovered>
      <SPPRecovered>{eps_data.get('spp_recovered', 0):.2f}</SPPRecovered>
      <SAPRecovered>{eps_data.get('sap_recovered', 0):.2f}</SAPRecovered>
      <ShPPRecovered>{eps_data.get('shpp_recovered', 0):.2f}</ShPPRecovered>
      <NICCompensationOnSMP>{eps_data.get('nic_compensation', 0):.2f}</NICCompensationOnSMP>
      <CISDeductionsSuffered>{eps_data.get('cis_deductions', 0):.2f}</CISDeductionsSuffered>
    </RecoverableAmountsYTD>"""
        
        if eps_data.get('final_submission'):
            xml_content += """
    <FinalSubmission>
      <BecauseSchemeCeased>yes</BecauseSchemeCeased>
    </FinalSubmission>"""
        
        xml_content += """
  </EmployerPaymentSummary>
</IRenvelope>"""
        
        return xml_content
    
    async def poll_submission_status(self, poll_url: str) -> Dict[str, Any]:
        """Poll HMRC for submission status (test mode returns mock response)"""
        # In production, this would make an actual HTTP request to HMRC
        # For test mode, we return a mock accepted response
        return {
            "status": "accepted",
            "message": "Submission accepted by HMRC (TEST MODE)",
            "timestamp": now_iso()
        }


hmrc_service = HMRCService(use_production=False)


router = APIRouter(prefix="/hmrc", tags=["HMRC RTI"])


# ==================== VALIDATION ====================

@router.post("/validate/{payrun_id}")
async def validate_payrun_for_rti(
    payrun_id: str,
    user: User = Depends(require_payroll)
):
    """
    Validate a pay run for HMRC RTI submission.
    Returns validation errors and warnings.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Validate
    result = await hmrc_service.validate_fps(company, payrun, employees, payslips)
    
    return result


@router.get("/health-check/{payrun_id}", response_model=PayrollHealthCheckResult)
async def payroll_health_check(
    payrun_id: str,
    user: User = Depends(require_payroll)
):
    """
    Comprehensive health check before RTI submission.
    Checks data quality, anomalies, and compliance issues.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    issues = []
    score = 100
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Check each employee
    for emp in employees:
        emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        
        # Missing NI number
        if not emp.get("ni_number"):
            issues.append(HealthCheckIssue(
                severity="critical",
                category="missing_data",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing NI Number",
                description=f"{emp_name} does not have a National Insurance number",
                action_required="Add NI number to employee record"
            ))
            score -= 10
        
        # Invalid NI format
        elif RTIValidator.validate_ni_number(emp.get("ni_number")) is not None:
            issues.append(HealthCheckIssue(
                severity="critical",
                category="compliance",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Invalid NI Number Format",
                description=f"{emp_name} has an invalid NI number format",
                action_required="Correct the NI number format"
            ))
            score -= 10
        
        # Missing tax code
        if not emp.get("tax_code"):
            issues.append(HealthCheckIssue(
                severity="warning",
                category="missing_data",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing Tax Code",
                description=f"{emp_name} does not have a tax code - defaulting to 1257L",
                action_required="Add correct tax code"
            ))
            score -= 5
        
        # Missing bank details
        if not emp.get("bank_account") or not emp.get("bank_sort_code"):
            issues.append(HealthCheckIssue(
                severity="warning",
                category="banking",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing Bank Details",
                description=f"{emp_name} has incomplete banking information",
                action_required="Add bank account and sort code"
            ))
            score -= 5
    
    # Check company HMRC details
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    if not company.get("paye_reference"):
        issues.append(HealthCheckIssue(
            severity="critical",
            category="compliance",
            employee_id=None,
            employee_name=None,
            title="Missing PAYE Reference",
            description="Company PAYE reference is required for HMRC submission",
            action_required="Add PAYE reference in company settings"
        ))
        score -= 20
    
    if not company.get("accounts_office_reference"):
        issues.append(HealthCheckIssue(
            severity="critical",
            category="compliance",
            employee_id=None,
            employee_name=None,
            title="Missing Accounts Office Reference",
            description="Accounts Office Reference is required for HMRC submission",
            action_required="Add Accounts Office Reference in company settings"
        ))
        score -= 20
    
    # Check for anomalies
    for ps in payslips:
        emp = next((e for e in employees if e.get("employee_id") == ps.get("employee_id")), None)
        if emp:
            emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
            
            # Check for unusually high/low pay
            expected_monthly = (emp.get("salary", 0) or 0) / 12
            actual_gross = ps.get("gross_pay", 0)
            
            if expected_monthly > 0:
                variance = abs(actual_gross - expected_monthly) / expected_monthly
                if variance > 0.5:  # More than 50% variance
                    issues.append(HealthCheckIssue(
                        severity="warning",
                        category="anomaly",
                        employee_id=emp.get("employee_id"),
                        employee_name=emp_name,
                        title="Pay Variance Detected",
                        description=f"{emp_name}'s gross pay (£{actual_gross:.2f}) varies significantly from expected (£{expected_monthly:.2f})",
                        action_required="Verify pay calculations are correct"
                    ))
                    score -= 3
    
    score = max(0, score)
    
    # Determine overall status
    critical_count = len([i for i in issues if i.severity == "critical"])
    warning_count = len([i for i in issues if i.severity == "warning"])
    
    if critical_count > 0:
        overall_status = "fail"
        can_proceed = False
    elif warning_count > 3:
        overall_status = "warning"
        can_proceed = True
    elif warning_count > 0:
        overall_status = "warning"
        can_proceed = True
    else:
        overall_status = "pass"
        can_proceed = True
    
    return PayrollHealthCheckResult(
        payrun_id=payrun_id,
        check_date=now_iso()[:10],
        overall_status=overall_status,
        score=score,
        issues=issues,
        can_proceed=can_proceed
    )


# ==================== FPS SUBMISSION ====================

@router.post("/fps/submit")
async def submit_fps(
    request: RTISubmissionRequest,
    user: User = Depends(require_payroll)
):
    """
    Submit Full Payment Submission (FPS) to HMRC.
    
    The FPS reports pay and deductions for all employees paid in this pay period.
    Must be submitted on or before each payday.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": request.payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Check if already submitted
    if payrun.get("rti_submitted"):
        raise HTTPException(
            status_code=400,
            detail="This pay run has already been submitted to HMRC"
        )
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": request.payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Validate before submission
    validation = await hmrc_service.validate_fps(company, payrun, employees, payslips)
    if not validation["valid"]:
        return {
            "success": False,
            "status": "validation_failed",
            "errors": validation["errors"],
            "warnings": validation["warnings"]
        }
    
    # Create submission record
    submission_id = generate_submission_id()
    now = now_utc()
    
    submission_doc = {
        "submission_id": submission_id,
        "company_id": user.company_id,
        "payrun_id": request.payrun_id,
        "submission_type": "FPS",
        "status": RTIStatus.VALIDATING,
        "validation_errors": [],
        "validation_warnings": validation.get("warnings", []),
        "test_mode": request.test_mode,
        "approved_by": user.user_id,
        "approved_at": now.isoformat(),
        "created_by": user.user_id,
        "created_at": now.isoformat()
    }
    await db.rti_submissions.insert_one(submission_doc)
    
    # Generate XML
    credentials = {
        "sender_id": company.get("hmrc_sender_id", ""),
        "password": company.get("hmrc_password", "")
    }
    
    try:
        xml_content = await hmrc_service.generate_fps_xml(
            company, payrun, employees, payslips, credentials
        )
        payload_hash = hashlib.sha256(xml_content.encode()).hexdigest()
        # Store XML for reference
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"xml_content": xml_content, "payload_hash": payload_hash, "status": RTIStatus.VALIDATED}}
        )
        
        # Submit to HMRC (test mode)
        if request.test_mode:
            result = await hmrc_service.submit_to_hmrc(xml_content, "FPS")
            
            if result["success"]:
                await db.rti_submissions.update_one(
                    {"submission_id": submission_id},
                    {
                        "$set": {
                            "status": RTIStatus.SUBMITTED,
                            "correlation_id": result.get("correlation_id"),
                            "poll_url": result.get("poll_url"),
                            "hmrc_response": result,
                            "submitted_at": now.isoformat()
                        }
                    }
                )
                
                # Mark pay run as submitted
                await db.pay_runs.update_one(
                    {"payrun_id": request.payrun_id},
                    {
                        "$set": {
                            "rti_submitted": True,
                            "rti_submission_id": submission_id,
                            "status": "submitted"
                        }
                    }
                )
                
                return {
                    "success": True,
                    "submission_id": submission_id,
                    "status": "submitted",
                    "correlation_id": result.get("correlation_id"),
                    "message": result.get("message"),
                    "test_mode": request.test_mode
                }
            else:
                await db.rti_submissions.update_one(
                    {"submission_id": submission_id},
                    {"$set": {"status": RTIStatus.ERROR, "hmrc_response": result}}
                )
                return {
                    "success": False,
                    "submission_id": submission_id,
                    "status": "error",
                    "error": result.get("error")
                }
        else:
            # Production submission requires additional setup
            return {
                "success": False,
                "submission_id": submission_id,
                "status": "pending",
                "message": "Production submissions require HMRC Gateway credentials. Please configure in settings."
            }
            
    except Exception as e:
        logger.error(f"FPS submission error: {e}")
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"status": RTIStatus.ERROR, "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EPS SUBMISSION ====================

@router.post("/eps/submit")
async def submit_eps(
    eps_data: EPSData,
    user: User = Depends(require_payroll)
):
    """
    Submit Employer Payment Summary (EPS) to HMRC.
    
    Use EPS to report:
    - Recoverable amounts (SMP, SPP, SAP, etc.)
    - No employees paid in a tax month
    - Final submission for the tax year
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    if not company.get("paye_reference"):
        raise HTTPException(
            status_code=400,
            detail="PAYE reference is required for EPS submission"
        )
    
    # Create submission record
    submission_id = generate_submission_id()
    now = now_utc()
    
    # Determine tax month and year
    tax_month = hmrc_service.get_tax_month(now.isoformat()[:10])
    tax_year = hmrc_service.get_tax_year(now.isoformat()[:10])
    
    submission_doc = {
        "submission_id": submission_id,
        "company_id": user.company_id,
        "payrun_id": None,
        "submission_type": "EPS",
        "status": RTIStatus.VALIDATING,
        "tax_month": tax_month,
        "tax_year": tax_year,
        "eps_data": eps_data.dict(),
        "created_by": user.user_id,
        "created_at": now.isoformat()
    }
    await db.rti_submissions.insert_one(submission_doc)
    
    # Generate XML
    credentials = {
        "sender_id": company.get("hmrc_sender_id", ""),
        "password": company.get("hmrc_password", "")
    }
    
    try:
        xml_content = await hmrc_service.generate_eps_xml(
            company, tax_month, tax_year, eps_data.dict(), credentials
        )
        payload_hash = hashlib.sha256(xml_content.encode()).hexdigest()
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"xml_content": xml_content, "payload_hash": payload_hash, "status": RTIStatus.VALIDATED}}
        )
        
        # Submit (test mode only for now)
        result = await hmrc_service.submit_to_hmrc(xml_content, "EPS")
        
        if result["success"]:
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {
                    "$set": {
                        "status": RTIStatus.SUBMITTED,
                        "correlation_id": result.get("correlation_id"),
                        "hmrc_response": result,
                        "submitted_at": now.isoformat()
                    }
                }
            )
            
            return {
                "success": True,
                "submission_id": submission_id,
                "status": "submitted",
                "tax_month": tax_month,
                "tax_year": tax_year,
                "message": result.get("message")
            }
        else:
            return {
                "success": False,
                "submission_id": submission_id,
                "error": result.get("error")
            }
            
    except Exception as e:
        logger.error(f"EPS submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SUBMISSION STATUS ====================

@router.get("/submissions", response_model=List[RTISubmission])
async def get_rti_submissions(
    limit: int = 50,
    user: User = Depends(require_payroll)
):
    """Get RTI submission history"""
    if not user.company_id:
        return []
    
    submissions = await db.rti_submissions.find(
        {"company_id": user.company_id},
        {"_id": 0, "xml_content": 0}  # Exclude large XML
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for sub in submissions:
        if isinstance(sub.get("created_at"), str):
            sub["created_at"] = datetime.fromisoformat(sub["created_at"])
        if isinstance(sub.get("submitted_at"), str):
            sub["submitted_at"] = datetime.fromisoformat(sub["submitted_at"])
    
    return [RTISubmission(**sub) for sub in submissions]


@router.get("/submissions/{submission_id}")
async def get_rti_submission(
    submission_id: str,
    user: User = Depends(require_payroll)
):
    """Get RTI submission details"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission


@router.post("/submissions/{submission_id}/poll")
async def poll_submission_status(
    submission_id: str,
    user: User = Depends(require_payroll)
):
    """Poll HMRC for submission status update"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    poll_url = submission.get("poll_url")
    if not poll_url:
        return {"status": submission.get("status"), "message": "No poll URL available"}
    
    # Poll HMRC
    result = await hmrc_service.poll_submission_status(poll_url)
    
    # Update status
    new_status = RTIStatus.ACCEPTED if result.get("status") == "accepted" else submission.get("status")
    
    await db.rti_submissions.update_one(
        {"submission_id": submission_id},
        {
            "$set": {
                "status": new_status,
                "poll_response": result,
                "accepted_at": datetime.now(timezone.utc).isoformat() if new_status == RTIStatus.ACCEPTED else None
            }
        }
    )
    
    return {
        "submission_id": submission_id,
        "status": new_status,
        "hmrc_response": result
    }


# ===========================================================================
# HMRC RTI CONFIGURATION — Sandbox / Production mode management
# ===========================================================================

class RTIConfigUpdate(BaseModel):
    rti_mode: Optional[str] = None          # "sandbox" | "production"
    gateway_user_id: Optional[str] = None
    gateway_password: Optional[str] = None  # write-only; stored hashed
    paye_reference: Optional[str] = None
    accounts_office_ref: Optional[str] = None
    employer_name: Optional[str] = None
    employer_address: Optional[dict] = None
    sender_id: Optional[str] = None


GO_LIVE_CHECKLIST_ITEMS = [
    {"key": "test_scenarios_passed", "label": "All 20 sandbox test scenarios passed (T01–T20)", "required": True},
    {"key": "credentials_verified", "label": "Live Government Gateway credentials verified", "required": True},
    {"key": "paye_reference_confirmed", "label": "PAYE reference confirmed with HMRC", "required": True},
    {"key": "accounts_office_ref_confirmed", "label": "Accounts Office Reference confirmed", "required": True},
    {"key": "employer_details_accurate", "label": "Employer name and address match HMRC records", "required": True},
    {"key": "employee_data_validated", "label": "All employee NI numbers and tax codes validated", "required": True},
    {"key": "first_fps_dry_run_passed", "label": "First FPS dry-run passed without errors", "required": True},
    {"key": "eps_configuration_verified", "label": "EPS configuration tested in sandbox", "required": True},
    {"key": "leaver_process_tested", "label": "Leaver FPS process tested", "required": True},
    {"key": "p45_generation_verified", "label": "P45 generation verified", "required": True},
    {"key": "bank_details_encrypted", "label": "Bank details encrypted at rest", "required": True},
    {"key": "audit_trail_active", "label": "RTI audit trail confirmed active", "required": True},
    {"key": "webhook_alerts_configured", "label": "Submission status webhook alerts configured", "required": False},
    {"key": "team_briefed", "label": "Payroll team briefed on live RTI workflow", "required": False},
    {"key": "rollback_plan_documented", "label": "Rollback plan documented in case of submission failure", "required": True},
]


async def _require_payroll_admin(request: Request) -> User:
    """Require owner, admin, or payroll_admin role for RTI config."""
    user = await get_current_user(request)
    if user.role not in ("owner", "admin", "payroll_admin"):
        raise HTTPException(status_code=403, detail="Payroll admin access required")
    return user


@router.get("/rti-config")
async def get_rti_config(user: User = Depends(_require_payroll_admin)):
    """
    Get the company's HMRC RTI configuration.
    Gateway password is never returned — only a boolean indicating if it is set.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    cfg = await db.hmrc_rti_config.find_one({"company_id": user.company_id}, {"_id": 0}) or {}

    # Mask sensitive fields — never return password hash; mask gateway_user_id to last 4 chars
    safe = {k: v for k, v in cfg.items() if k not in ("gateway_password_hash",)}
    safe["gateway_password_set"] = bool(cfg.get("gateway_password_hash"))
    if safe.get("gateway_user_id") and len(safe["gateway_user_id"]) > 4:
        uid = safe["gateway_user_id"]
        safe["gateway_user_id_masked"] = f"{'*' * (len(uid) - 4)}{uid[-4:]}"
    # Return the unmasked value for the form pre-fill (owner/admin can see it to edit)
    # but flag that it's been set
    safe.setdefault("rti_mode", "sandbox")
    safe.setdefault("software_name", "RealtouchHR")

    # Merge with go-live checklist — return as dict keyed by item key for easy frontend use
    checklist_state = cfg.get("readiness_checklist") or {}
    safe["go_live_checklist"] = {
        item["key"]: bool(checklist_state.get(item["key"]))
        for item in GO_LIVE_CHECKLIST_ITEMS
    }
    required_done = all(
        checklist_state.get(i["key"])
        for i in GO_LIVE_CHECKLIST_ITEMS
        if i["required"]
    )
    safe["ready_for_go_live"] = required_done

    return safe


@router.put("/rti-config")
async def update_rti_config(body: RTIConfigUpdate, user: User = Depends(_require_payroll_admin)):
    """
    Update HMRC RTI configuration.

    SECURITY RULES enforced server-side:
    - Switching to production mode requires all required go-live checklist items completed.
    - Gateway password is hashed before storage; never exposed in responses or logs.
    - Credentials must not appear in logs — this endpoint strips them before logging.
    """
    import bcrypt as _bcrypt
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    cfg = await db.hmrc_rti_config.find_one({"company_id": user.company_id}, {"_id": 0}) or {}
    checklist_state = cfg.get("readiness_checklist") or {}

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if body.rti_mode is not None:
        if body.rti_mode not in ("sandbox", "production"):
            raise HTTPException(status_code=400, detail="rti_mode must be 'sandbox' or 'production'")
        if body.rti_mode == "production":
            required_done = all(
                checklist_state.get(i["key"])
                for i in GO_LIVE_CHECKLIST_ITEMS
                if i["required"]
            )
            if not required_done:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot switch to production mode: required go-live checklist items are not all completed."
                )
        updates["rti_mode"] = body.rti_mode

    if body.gateway_user_id is not None:
        updates["gateway_user_id"] = body.gateway_user_id

    if body.gateway_password is not None:
        # Hash before storing — never log the raw password
        hashed = _bcrypt.hashpw(body.gateway_password.encode(), _bcrypt.gensalt()).decode()
        updates["gateway_password_hash"] = hashed

    for field in ("paye_reference", "accounts_office_ref", "employer_name", "employer_address", "sender_id"):
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val

    existing = await db.hmrc_rti_config.find_one({"company_id": user.company_id}, {"_id": 0})
    if existing:
        await db.hmrc_rti_config.update_one({"company_id": user.company_id}, {"$set": updates})
    else:
        updates.update({
            "config_id": f"rticfg_{uuid.uuid4().hex[:12]}",
            "company_id": user.company_id,
            "rti_mode": updates.get("rti_mode", "sandbox"),
            "software_name": "RealtouchHR",
            "go_live_approved": False,
            "readiness_checklist": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.hmrc_rti_config.insert_one(updates)

    # Audit — exclude credentials from log details
    await db.audit_log.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "action": "hmrc_rti_config_updated",
        "entity_type": "hmrc_rti_config",
        "entity_id": user.company_id,
        "details": {
            "fields_updated": [k for k in updates if k not in ("gateway_password_hash", "updated_at")],
            "rti_mode": updates.get("rti_mode"),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"message": "RTI configuration updated", "rti_mode": updates.get("rti_mode", cfg.get("rti_mode", "sandbox"))}


class ChecklistItemUpdate(BaseModel):
    completed: bool = True


@router.patch("/rti-config/checklist/{item_key}")
async def update_go_live_checklist_item(
    item_key: str,
    body: ChecklistItemUpdate = ChecklistItemUpdate(),
    user: User = Depends(_require_payroll_admin),
):
    """
    Toggle a go-live checklist item. Returns updated checklist so UI can sync.
    Only owners and admins may approve checklist items.
    """
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can approve go-live checklist items")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    valid_keys = {i["key"] for i in GO_LIVE_CHECKLIST_ITEMS}
    if item_key not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Unknown checklist item: {item_key}")

    cfg = await db.hmrc_rti_config.find_one({"company_id": user.company_id}, {"_id": 0})
    if cfg:
        checklist = cfg.get("readiness_checklist") or {}
        # Toggle: if no body provided (bare PATCH), flip the current value
        current = checklist.get(item_key, False)
        checklist[item_key] = not current
        await db.hmrc_rti_config.update_one(
            {"company_id": user.company_id},
            {"$set": {"readiness_checklist": checklist, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    else:
        checklist = {item_key: True}
        await db.hmrc_rti_config.insert_one({
            "config_id": f"rticfg_{uuid.uuid4().hex[:12]}",
            "company_id": user.company_id,
            "rti_mode": "sandbox",
            "software_name": "RealtouchHR",
            "go_live_approved": False,
            "readiness_checklist": checklist,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    return {"go_live_checklist": checklist}


@router.post("/rti-config/test-connection")
async def test_rti_connection(
    user: User = Depends(_require_payroll_admin),
):
    """
    Test the HMRC RTI configuration without submitting any payroll data.
    Validates that credentials and PAYE references are present and correctly formatted.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    cfg = await db.hmrc_rti_config.find_one({"company_id": user.company_id}, {"_id": 0}) or {}
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0}) or {}

    issues = []

    # Check gateway credentials
    if not cfg.get("gateway_user_id"):
        issues.append({"field": "gateway_user_id", "message": "Government Gateway User ID is not configured"})
    if not cfg.get("gateway_password_hash"):
        issues.append({"field": "gateway_password", "message": "Government Gateway Password is not configured"})

    # Check PAYE reference (pattern: e.g. 123/AB12345)
    import re
    paye = company.get("paye_reference") or cfg.get("paye_reference") or ""
    if not paye:
        issues.append({"field": "paye_reference", "message": "PAYE Reference is missing — configure in Settings"})
    elif not re.match(r"^\d{3}/[A-Z]{2}\d+$", paye.upper().replace(" ", "")):
        issues.append({"field": "paye_reference", "message": f"PAYE Reference format looks incorrect: '{paye}'. Expected format: 123/AB12345"})

    # Check Accounts Office Reference
    aor = company.get("accounts_office_reference") or cfg.get("accounts_office_reference") or ""
    if not aor:
        issues.append({"field": "accounts_office_reference", "message": "Accounts Office Reference is missing — configure in Settings"})
    elif len(aor.replace(" ", "")) < 13:
        issues.append({"field": "accounts_office_reference", "message": "Accounts Office Reference appears too short"})

    # Check employer name
    employer_name = company.get("name") or ""
    if not employer_name:
        issues.append({"field": "employer_name", "message": "Employer name is missing from company profile"})

    mode = cfg.get("rti_mode", "sandbox")
    passed = len(issues) == 0

    # Audit log
    await db.audit_log.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "action": "HMRC_RTI_CONNECTION_TEST",
        "entity_type": "hmrc_rti_config",
        "details": {"passed": passed, "issues_count": len(issues), "mode": mode},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "passed": passed,
        "mode": mode,
        "issues": issues,
        "message": "Configuration validated successfully — ready for sandbox testing." if passed else f"{len(issues)} configuration issue(s) found.",
    }
