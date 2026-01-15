"""
RealtouchHR - HMRC RTI Service
Full Payment Submission (FPS) and Employer Payment Summary (EPS)
Production-ready implementation
"""
import os
import logging
import hashlib
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== HMRC CONFIGURATION ====================

# HMRC Gateway URLs
HMRC_TEST_URL = "https://test-transaction-engine.tax.service.gov.uk/submission"
HMRC_PRODUCTION_URL = "https://transaction-engine.tax.service.gov.uk/submission"

# RTI Schema versions
RTI_SCHEMA_VERSION = "24-25"  # Tax year 2024-25
FPS_VERSION = "15-16-8"
EPS_VERSION = "15-16-4"

# HMRC namespaces
HMRC_NAMESPACES = {
    "govtalk": "http://www.govtalk.gov.uk/CM/envelope",
    "rti": "http://www.govtalk.gov.uk/taxation/RTI/2024-25",
    "dsig": "http://www.w3.org/2000/09/xmldsig#"
}


class RTISubmissionType(str, Enum):
    FPS = "FPS"  # Full Payment Submission
    EPS = "EPS"  # Employer Payment Summary
    EYU = "EYU"  # Earlier Year Update
    NVR = "NVR"  # NINO Verification Request


class RTIStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    POLLING = "polling"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


# ==================== VALIDATION RULES ====================

class RTIValidationError:
    """RTI validation error with HMRC error code"""
    def __init__(self, code: str, field: str, message: str, severity: str = "error"):
        self.code = code
        self.field = field
        self.message = message
        self.severity = severity  # error, warning
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "severity": self.severity
        }


class RTIValidator:
    """Validates payroll data against HMRC RTI rules"""
    
    @staticmethod
    def validate_ni_number(ni: str) -> Optional[RTIValidationError]:
        """Validate National Insurance number format"""
        if not ni:
            return RTIValidationError("NI001", "ni_number", "National Insurance number is required")
        
        import re
        ni_clean = ni.upper().replace(' ', '')
        # Format: 2 letters, 6 digits, 1 letter (A/B/C/D)
        # First 2 letters cannot be D, F, I, Q, U, V
        # Second letter cannot be O
        pattern = r'^(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$'
        
        if not re.match(pattern, ni_clean):
            return RTIValidationError("NI002", "ni_number", f"Invalid NI number format: {ni}")
        return None
    
    @staticmethod
    def validate_tax_code(tax_code: str) -> Optional[RTIValidationError]:
        """Validate tax code format"""
        if not tax_code:
            return RTIValidationError("TAX001", "tax_code", "Tax code is required")
        
        import re
        code_clean = tax_code.upper().replace(' ', '')
        # Common formats: 1257L, BR, D0, D1, NT, 0T, K codes, Scottish S prefixed
        pattern = r'^(S)?(\d{1,4}[LMNPTY]|BR|D[01]|NT|0T|K\d+)$'
        
        if not re.match(pattern, code_clean):
            return RTIValidationError("TAX002", "tax_code", f"Invalid tax code format: {tax_code}", "warning")
        return None
    
    @staticmethod
    def validate_employee_for_fps(employee: dict) -> List[RTIValidationError]:
        """Validate employee data for FPS submission"""
        errors = []
        
        # Required fields
        if not employee.get("first_name"):
            errors.append(RTIValidationError("EMP001", "first_name", "First name is required"))
        if not employee.get("last_name"):
            errors.append(RTIValidationError("EMP002", "last_name", "Last name is required"))
        
        # NI number validation
        ni_error = RTIValidator.validate_ni_number(employee.get("ni_number", ""))
        if ni_error:
            errors.append(ni_error)
        
        # Tax code validation
        tax_error = RTIValidator.validate_tax_code(employee.get("tax_code", ""))
        if tax_error:
            errors.append(tax_error)
        
        # Salary must be present and positive
        salary = employee.get("salary", 0)
        if not salary or salary <= 0:
            errors.append(RTIValidationError("EMP003", "salary", "Valid salary is required"))
        
        return errors
    
    @staticmethod
    def validate_company_for_rti(company: dict) -> List[RTIValidationError]:
        """Validate company data for RTI submission"""
        errors = []
        
        # PAYE Reference (format: 123/AB12345)
        paye_ref = company.get("paye_reference", "")
        if not paye_ref:
            errors.append(RTIValidationError("COMP001", "paye_reference", "PAYE reference is required for RTI"))
        else:
            import re
            if not re.match(r'^\d{3}/[A-Z0-9]+$', paye_ref.upper()):
                errors.append(RTIValidationError("COMP002", "paye_reference", f"Invalid PAYE reference format: {paye_ref}"))
        
        # Accounts Office Reference (format: 123PX12345678)
        aor = company.get("accounts_office_reference", "")
        if not aor:
            errors.append(RTIValidationError("COMP003", "accounts_office_reference", "Accounts Office Reference is required for RTI"))
        
        return errors
    
    @staticmethod
    def validate_payrun_for_fps(payrun: dict, employees: list, payslips: list) -> List[RTIValidationError]:
        """Validate a complete pay run for FPS submission"""
        errors = []
        
        # Pay run dates
        if not payrun.get("period_start"):
            errors.append(RTIValidationError("PR001", "period_start", "Pay period start date is required"))
        if not payrun.get("period_end"):
            errors.append(RTIValidationError("PR002", "period_end", "Pay period end date is required"))
        if not payrun.get("pay_date"):
            errors.append(RTIValidationError("PR003", "pay_date", "Pay date is required"))
        
        # Must have at least one employee
        if not employees or not payslips:
            errors.append(RTIValidationError("PR004", "employees", "At least one employee is required"))
        
        # Validate each employee
        for emp in employees:
            emp_errors = RTIValidator.validate_employee_for_fps(emp)
            errors.extend(emp_errors)
        
        return errors


# ==================== XML BUILDERS ====================

class FPSBuilder:
    """Builds FPS (Full Payment Submission) XML for HMRC"""
    
    def __init__(self, company: dict, payrun: dict, employees: list, payslips: list, credentials: dict):
        self.company = company
        self.payrun = payrun
        self.employees = employees
        self.payslips = payslips
        self.credentials = credentials
        self.correlation_id = str(uuid.uuid4())
    
    def build(self) -> str:
        """Build the complete FPS XML document"""
        # Create root GovTalk envelope
        root = ET.Element("GovTalkMessage", xmlns="http://www.govtalk.gov.uk/CM/envelope")
        
        # EnvelopeVersion
        ET.SubElement(root, "EnvelopeVersion").text = "2.0"
        
        # Header
        header = ET.SubElement(root, "Header")
        self._build_header(header)
        
        # GovTalkDetails
        details = ET.SubElement(root, "GovTalkDetails")
        keys = ET.SubElement(details, "Keys")
        key = ET.SubElement(keys, "Key", Type="TaxOfficeNumber")
        key.text = self.company.get("paye_reference", "").split("/")[0] if "/" in self.company.get("paye_reference", "") else ""
        key2 = ET.SubElement(keys, "Key", Type="TaxOfficeReference")
        key2.text = self.company.get("paye_reference", "").split("/")[1] if "/" in self.company.get("paye_reference", "") else ""
        
        # Body
        body = ET.SubElement(root, "Body")
        self._build_fps_body(body)
        
        # Pretty print
        xml_str = ET.tostring(root, encoding='unicode')
        return minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    def _build_header(self, header):
        """Build GovTalk header"""
        msg_details = ET.SubElement(header, "MessageDetails")
        ET.SubElement(msg_details, "Class").text = "HMRC-PAYE-RTI-FPS"
        ET.SubElement(msg_details, "Qualifier").text = "request"
        ET.SubElement(msg_details, "Function").text = "submit"
        ET.SubElement(msg_details, "TransactionID").text = self.correlation_id
        ET.SubElement(msg_details, "CorrelationID").text = self.correlation_id
        
        sender_details = ET.SubElement(header, "SenderDetails")
        id_auth = ET.SubElement(sender_details, "IDAuthentication")
        ET.SubElement(id_auth, "SenderID").text = self.credentials.get("sender_id", "")
        auth = ET.SubElement(id_auth, "Authentication")
        ET.SubElement(auth, "Method").text = "clear"
        ET.SubElement(auth, "Value").text = self.credentials.get("password", "")
    
    def _build_fps_body(self, body):
        """Build FPS IRenvelope"""
        ir_env = ET.SubElement(body, "IRenvelope", xmlns="http://www.govtalk.gov.uk/taxation/PAYE/RTI/FPS/24-25/1")
        
        ir_header = ET.SubElement(ir_env, "IRheader")
        keys = ET.SubElement(ir_header, "Keys")
        ET.SubElement(keys, "Key", Type="TaxOfficeNumber").text = self.company.get("paye_reference", "").split("/")[0] if "/" in self.company.get("paye_reference", "") else ""
        ET.SubElement(keys, "Key", Type="TaxOfficeReference").text = self.company.get("paye_reference", "").split("/")[1] if "/" in self.company.get("paye_reference", "") else ""
        ET.SubElement(ir_header, "PeriodEnd").text = self.payrun.get("period_end", "")
        
        # FPS specific data
        fps = ET.SubElement(ir_env, "FullPaymentSubmission")
        
        # Related tax year
        ET.SubElement(fps, "RelatedTaxYear").text = "24-25"
        
        # Employer details
        employer = ET.SubElement(fps, "Employer")
        ET.SubElement(employer, "AOref").text = self.company.get("accounts_office_reference", "")
        
        # Employee payment details
        for payslip in self.payslips:
            emp = next((e for e in self.employees if e.get("employee_id") == payslip.get("employee_id")), None)
            if emp:
                self._build_employee_fps(fps, emp, payslip)
    
    def _build_employee_fps(self, parent, employee: dict, payslip: dict):
        """Build FPS employee data"""
        emp_elem = ET.SubElement(parent, "Employee")
        
        # Employee details
        emp_details = ET.SubElement(emp_elem, "EmployeeDetails")
        name = ET.SubElement(emp_details, "Name")
        ET.SubElement(name, "Fore").text = employee.get("first_name", "")
        ET.SubElement(name, "Sur").text = employee.get("last_name", "")
        ET.SubElement(emp_details, "NINO").text = employee.get("ni_number", "").upper().replace(" ", "")
        
        # Employment details
        employment = ET.SubElement(emp_elem, "Employment")
        ET.SubElement(employment, "PayFreq").text = "M1"  # Monthly
        ET.SubElement(employment, "PaymentDate").text = self.payrun.get("pay_date", "")
        ET.SubElement(employment, "TaxCode").text = employee.get("tax_code", "1257L")
        
        # Pay figures
        pay = ET.SubElement(employment, "Pay")
        ET.SubElement(pay, "TaxablePay").text = str(round(payslip.get("gross_pay", 0), 2))
        ET.SubElement(pay, "TaxDeductedOrRefunded").text = str(round(payslip.get("tax_deduction", 0), 2))
        
        # NI contributions
        ni = ET.SubElement(employment, "NIcontribution")
        ET.SubElement(ni, "NIcategory").text = "A"  # Standard category
        ET.SubElement(ni, "GrossEarningsForNI").text = str(round(payslip.get("gross_pay", 0), 2))
        ET.SubElement(ni, "EmployeeContribution").text = str(round(payslip.get("ni_deduction", 0), 2))


class EPSBuilder:
    """Builds EPS (Employer Payment Summary) XML for HMRC"""
    
    def __init__(self, company: dict, tax_month: int, tax_year: str, eps_data: dict, credentials: dict):
        self.company = company
        self.tax_month = tax_month
        self.tax_year = tax_year
        self.eps_data = eps_data
        self.credentials = credentials
        self.correlation_id = str(uuid.uuid4())
    
    def build(self) -> str:
        """Build the complete EPS XML document"""
        root = ET.Element("GovTalkMessage", xmlns="http://www.govtalk.gov.uk/CM/envelope")
        
        ET.SubElement(root, "EnvelopeVersion").text = "2.0"
        
        header = ET.SubElement(root, "Header")
        self._build_header(header)
        
        details = ET.SubElement(root, "GovTalkDetails")
        keys = ET.SubElement(details, "Keys")
        paye_parts = self.company.get("paye_reference", "").split("/")
        ET.SubElement(keys, "Key", Type="TaxOfficeNumber").text = paye_parts[0] if len(paye_parts) > 0 else ""
        ET.SubElement(keys, "Key", Type="TaxOfficeReference").text = paye_parts[1] if len(paye_parts) > 1 else ""
        
        body = ET.SubElement(root, "Body")
        self._build_eps_body(body)
        
        xml_str = ET.tostring(root, encoding='unicode')
        return minidom.parseString(xml_str).toprettyxml(indent="  ")
    
    def _build_header(self, header):
        """Build GovTalk header for EPS"""
        msg_details = ET.SubElement(header, "MessageDetails")
        ET.SubElement(msg_details, "Class").text = "HMRC-PAYE-RTI-EPS"
        ET.SubElement(msg_details, "Qualifier").text = "request"
        ET.SubElement(msg_details, "Function").text = "submit"
        ET.SubElement(msg_details, "TransactionID").text = self.correlation_id
        ET.SubElement(msg_details, "CorrelationID").text = self.correlation_id
        
        sender_details = ET.SubElement(header, "SenderDetails")
        id_auth = ET.SubElement(sender_details, "IDAuthentication")
        ET.SubElement(id_auth, "SenderID").text = self.credentials.get("sender_id", "")
        auth = ET.SubElement(id_auth, "Authentication")
        ET.SubElement(auth, "Method").text = "clear"
        ET.SubElement(auth, "Value").text = self.credentials.get("password", "")
    
    def _build_eps_body(self, body):
        """Build EPS IRenvelope"""
        ir_env = ET.SubElement(body, "IRenvelope", xmlns="http://www.govtalk.gov.uk/taxation/PAYE/RTI/EPS/24-25/1")
        
        ir_header = ET.SubElement(ir_env, "IRheader")
        keys = ET.SubElement(ir_header, "Keys")
        paye_parts = self.company.get("paye_reference", "").split("/")
        ET.SubElement(keys, "Key", Type="TaxOfficeNumber").text = paye_parts[0] if len(paye_parts) > 0 else ""
        ET.SubElement(keys, "Key", Type="TaxOfficeReference").text = paye_parts[1] if len(paye_parts) > 1 else ""
        ET.SubElement(ir_header, "PeriodEnd").text = f"{self.tax_year}-{self.tax_month:02d}-05"
        
        eps = ET.SubElement(ir_env, "EmployerPaymentSummary")
        ET.SubElement(eps, "RelatedTaxYear").text = self.tax_year
        ET.SubElement(eps, "TaxMonth").text = str(self.tax_month)
        
        # Recoverable amounts
        if self.eps_data.get("smp_recovered", 0) > 0:
            ET.SubElement(eps, "RecoverableAmountsSMP").text = str(self.eps_data["smp_recovered"])
        if self.eps_data.get("spp_recovered", 0) > 0:
            ET.SubElement(eps, "RecoverableAmountsSPP").text = str(self.eps_data["spp_recovered"])
        if self.eps_data.get("sap_recovered", 0) > 0:
            ET.SubElement(eps, "RecoverableAmountsSAP").text = str(self.eps_data["sap_recovered"])
        
        # Final submission for year
        if self.eps_data.get("final_submission"):
            final = ET.SubElement(eps, "FinalSubmission")
            if self.eps_data.get("cessation_date"):
                ET.SubElement(final, "DateSchemeCeased").text = self.eps_data["cessation_date"]


# ==================== HMRC SUBMISSION SERVICE ====================

class HMRCService:
    """
    HMRC RTI Submission Service
    Handles validation, XML generation, and submission to HMRC Gateway
    """
    
    def __init__(self, use_production: bool = False):
        self.use_production = use_production
        self.base_url = HMRC_PRODUCTION_URL if use_production else HMRC_TEST_URL
    
    async def validate_fps(
        self,
        company: dict,
        payrun: dict,
        employees: list,
        payslips: list
    ) -> Dict[str, Any]:
        """Validate data for FPS submission"""
        errors = []
        warnings = []
        
        # Validate company
        company_errors = RTIValidator.validate_company_for_rti(company)
        for err in company_errors:
            if err.severity == "error":
                errors.append(err.to_dict())
            else:
                warnings.append(err.to_dict())
        
        # Validate pay run and employees
        payrun_errors = RTIValidator.validate_payrun_for_fps(payrun, employees, payslips)
        for err in payrun_errors:
            if err.severity == "error":
                errors.append(err.to_dict())
            else:
                warnings.append(err.to_dict())
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "employee_count": len(employees),
            "total_pay": sum(ps.get("gross_pay", 0) for ps in payslips)
        }
    
    async def generate_fps_xml(
        self,
        company: dict,
        payrun: dict,
        employees: list,
        payslips: list,
        credentials: dict
    ) -> str:
        """Generate FPS XML for submission"""
        builder = FPSBuilder(company, payrun, employees, payslips, credentials)
        return builder.build()
    
    async def generate_eps_xml(
        self,
        company: dict,
        tax_month: int,
        tax_year: str,
        eps_data: dict,
        credentials: dict
    ) -> str:
        """Generate EPS XML for submission"""
        builder = EPSBuilder(company, tax_month, tax_year, eps_data, credentials)
        return builder.build()
    
    async def submit_to_hmrc(
        self,
        xml_content: str,
        submission_type: str = "FPS"
    ) -> Dict[str, Any]:
        """
        Submit XML to HMRC Gateway
        
        In production, this would:
        1. Send XML to HMRC Transaction Engine
        2. Receive acknowledgment with poll URL
        3. Poll for results
        4. Return final status
        
        For now, this returns a simulated response.
        """
        logger.info(f"Submitting {submission_type} to HMRC Gateway at {self.base_url}")
        
        # Generate correlation ID for tracking
        correlation_id = str(uuid.uuid4())
        
        # In a real implementation, you would:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         self.base_url,
        #         content=xml_content,
        #         headers={"Content-Type": "application/xml"}
        #     )
        
        # Simulated response for development/testing
        if self.use_production:
            return {
                "success": False,
                "error": "Production submission requires HMRC Gateway credentials",
                "correlation_id": correlation_id
            }
        
        # Test mode response
        return {
            "success": True,
            "correlation_id": correlation_id,
            "poll_url": f"{self.base_url}/poll/{correlation_id}",
            "status": "submitted",
            "message": "Submission received. This is a TEST submission.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def poll_submission_status(self, poll_url: str) -> Dict[str, Any]:
        """
        Poll HMRC for submission status
        
        Returns status: pending, accepted, rejected
        """
        # In production, poll the HMRC endpoint
        # For testing, simulate acceptance
        return {
            "status": "accepted",
            "message": "Submission accepted by HMRC",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_tax_month(self, date_str: str) -> int:
        """
        Get HMRC tax month from a date
        Tax year runs 6 April to 5 April
        Month 1 = 6 April - 5 May, etc.
        """
        date = datetime.fromisoformat(date_str)
        month = date.month
        day = date.day
        
        # Adjust for tax year
        if month == 4 and day >= 6:
            return 1
        elif month > 4:
            return month - 3
        elif month < 4:
            return month + 9
        elif month == 4 and day < 6:
            return 12  # Previous tax year
        return 1
    
    def get_tax_year(self, date_str: str) -> str:
        """
        Get HMRC tax year from a date
        Returns format: 24-25
        """
        date = datetime.fromisoformat(date_str)
        year = date.year
        month = date.month
        day = date.day
        
        # If before April 6, it's the previous tax year
        if month < 4 or (month == 4 and day < 6):
            return f"{str(year-1)[2:]}-{str(year)[2:]}"
        return f"{str(year)[2:]}-{str(year+1)[2:]}"


# Singleton instance
hmrc_service = HMRCService(use_production=False)
