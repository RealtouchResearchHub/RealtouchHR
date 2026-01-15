"""
RealtouchHR - Pydantic Models
All data models for the application
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    HR_MANAGER = "hr_manager"
    PAYROLL_ADMIN = "payroll_admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PayRunStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    PAID = "paid"


class RTISubmissionType(str, Enum):
    FPS = "FPS"  # Full Payment Submission
    EPS = "EPS"  # Employer Payment Summary
    EYU = "EYU"  # Earlier Year Update
    NVR = "NVR"  # NINO Verification Request


class RTISubmissionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


# ==================== AUTH MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: Optional[str] = None
    role: UserRole = UserRole.OWNER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "owner"
    company_id: Optional[str] = None
    employee_id: Optional[str] = None  # Links to employee record for self-service
    theme_preference: str = "light"
    created_at: datetime


class TokenResponse(BaseModel):
    token: str
    user: User


# ==================== COMPANY MODELS ====================

class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    address: Optional[str] = None
    payroll_frequency: str = "monthly"
    # HMRC Details
    paye_reference: Optional[str] = None
    accounts_office_reference: Optional[str] = None
    corporation_tax_reference: Optional[str] = None


class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_id: str
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    address: Optional[str] = None
    payroll_frequency: str = "monthly"
    owner_id: str
    setup_completed: bool = False
    # HMRC Details
    paye_reference: Optional[str] = None
    accounts_office_reference: Optional[str] = None
    corporation_tax_reference: Optional[str] = None
    # Multi-entity support
    parent_company_id: Optional[str] = None
    is_parent: bool = True
    created_at: datetime


# ==================== EMPLOYEE MODELS ====================

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    salary: Optional[float] = None
    ni_number: Optional[str] = None
    tax_code: Optional[str] = None
    bank_account: Optional[str] = None
    bank_sort_code: Optional[str] = None
    # Self-service access
    enable_self_service: bool = False


class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    employee_id: str
    company_id: str
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    salary: Optional[float] = None
    ni_number: Optional[str] = None
    tax_code: Optional[str] = None
    bank_account: Optional[str] = None
    bank_sort_code: Optional[str] = None
    status: str = "active"
    compliance_score: int = 0
    compliance_issues: List[str] = []
    # Self-service
    user_id: Optional[str] = None  # Links to user account for self-service
    enable_self_service: bool = False
    created_at: datetime
    updated_at: datetime


# ==================== LEAVE MODELS ====================

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: str
    end_date: str
    reason: Optional[str] = None


class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    leave_id: str
    employee_id: str
    company_id: str
    leave_type: str
    start_date: str
    end_date: str
    days: int
    reason: Optional[str] = None
    status: str = "pending"
    approved_by: Optional[str] = None
    created_at: datetime


class LeaveBalance(BaseModel):
    employee_id: str
    year: int
    annual_entitlement: int = 28  # UK statutory minimum
    used: int = 0
    pending: int = 0
    remaining: int = 28


# ==================== DOCUMENT MODELS ====================

class DocumentCreate(BaseModel):
    name: str
    doc_type: str
    content: Optional[str] = None
    employee_id: Optional[str] = None


class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_id: str
    company_id: str
    employee_id: Optional[str] = None
    name: str
    doc_type: str
    content: Optional[str] = None
    status: str = "draft"
    created_by: str
    created_at: datetime
    updated_at: datetime


# ==================== SHIFT/ROTA MODELS ====================

class ShiftCreate(BaseModel):
    employee_id: str
    date: str
    start_time: str
    end_time: str
    break_minutes: int = 0


class Shift(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shift_id: str
    company_id: str
    employee_id: str
    date: str
    start_time: str
    end_time: str
    break_minutes: int = 0
    status: str = "scheduled"
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    created_at: datetime


# ==================== TIMESHEET MODELS ====================

class TimesheetEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    timesheet_id: str
    company_id: str
    employee_id: str
    week_start: str
    hours_worked: float
    overtime_hours: float = 0
    status: str = "pending"
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== PAYROLL MODELS ====================

class PayRunCreate(BaseModel):
    period_start: str
    period_end: str
    pay_date: str


class PayRun(BaseModel):
    model_config = ConfigDict(extra="ignore")
    payrun_id: str
    company_id: str
    period_start: str
    period_end: str
    pay_date: str
    status: str = "draft"
    total_gross: float = 0
    total_tax: float = 0
    total_ni: float = 0
    total_net: float = 0
    employee_count: int = 0
    compliance_score: int = 0
    # HMRC RTI
    rti_submitted: bool = False
    rti_submission_id: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class PayslipPreview(BaseModel):
    employee_id: str
    employee_name: str
    gross_pay: float
    tax_deduction: float
    ni_deduction: float
    pension_deduction: float
    other_deductions: float
    net_pay: float
    overtime_pay: float = 0


# ==================== AUDIT MODELS ====================

class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    audit_id: str
    company_id: str
    user_id: str
    user_name: str
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, Any]
    reason: Optional[str] = None
    timestamp: datetime


# ==================== COMPLIANCE MODELS ====================

class ComplianceTask(BaseModel):
    model_config = ConfigDict(extra="ignore")
    task_id: str
    company_id: str
    title: str
    description: str
    priority: str
    status: str = "pending"
    due_date: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: datetime


# ==================== AI COPILOT MODELS ====================

class CopilotMessage(BaseModel):
    message: str
    context: Optional[str] = None


class CopilotResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    requires_approval: bool = False


# ==================== BULK IMPORT MODELS ====================

class BulkImportResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[str] = []
    imported_ids: List[str] = []


# ==================== NOTIFICATION MODELS ====================

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    notification_id: str
    company_id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    read: bool = False
    created_at: datetime


# ==================== ONBOARDING MODELS ====================

class OnboardingProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_id: str
    step: int
    completed_steps: List[str] = []
    first_employee_added: bool = False
    first_payrun_created: bool = False
    completed: bool = False


# ==================== HMRC RTI MODELS ====================

class HMRCCredentials(BaseModel):
    """HMRC Gateway credentials for RTI submissions"""
    sender_id: str
    password: str
    # For production use
    use_production: bool = False


class RTISubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    submission_id: str
    company_id: str
    payrun_id: str
    submission_type: str  # FPS, EPS, EYU, NVR
    status: str  # draft, validating, validated, submitting, submitted, accepted, rejected, error
    # Validation results
    validation_errors: List[Dict[str, Any]] = []
    validation_warnings: List[Dict[str, Any]] = []
    # HMRC response
    hmrc_response: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    poll_url: Optional[str] = None
    # Timestamps
    submitted_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime


class RTISubmissionRequest(BaseModel):
    payrun_id: str
    submission_type: str = "FPS"
    test_mode: bool = True


class FPSEmployeeData(BaseModel):
    """Full Payment Submission employee data"""
    employee_id: str
    ni_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    # Pay details
    taxable_pay: float
    tax_deducted: float
    ni_letters: str = "A"
    ni_earnings: float
    ni_employee_contribution: float
    ni_employer_contribution: float
    # Statutory payments
    ssp: float = 0
    smp: float = 0
    spp: float = 0
    sap: float = 0
    # Student loan
    student_loan_deduction: float = 0
    student_loan_plan: Optional[str] = None


class EPSData(BaseModel):
    """Employer Payment Summary data"""
    no_payment_dates: Optional[List[str]] = None
    period_of_inactivity: Optional[Dict[str, str]] = None
    # Recoverable amounts
    smp_recovered: float = 0
    spp_recovered: float = 0
    sap_recovered: float = 0
    shpp_recovered: float = 0
    nic_compensation: float = 0
    cis_deductions: float = 0
    # Final submission
    final_submission: bool = False
    cessation_date: Optional[str] = None


# ==================== PAYROLL HEALTH CHECK MODELS ====================

class HealthCheckIssue(BaseModel):
    severity: str  # critical, warning, info
    category: str  # missing_data, anomaly, compliance, banking
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    title: str
    description: str
    action_required: str


class PayrollHealthCheckResult(BaseModel):
    payrun_id: str
    check_date: str
    overall_status: str  # pass, warning, fail
    score: int
    issues: List[HealthCheckIssue]
    can_proceed: bool


# ==================== MULTI-CURRENCY MODELS ====================

class CurrencyInfo(BaseModel):
    code: str
    symbol: str
    name: str
    rate_to_gbp: float


class CurrencyConversion(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    converted_amount: float
    rate: float


# ==================== EMPLOYEE SELF-SERVICE MODELS ====================

class SelfServiceProfile(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    can_edit_personal: bool = True
    can_view_payslips: bool = True
    can_request_leave: bool = True


class SelfServicePayslip(BaseModel):
    payrun_id: str
    period_start: str
    period_end: str
    pay_date: str
    gross_pay: float
    net_pay: float
    status: str


class SelfServiceProfileUpdate(BaseModel):
    """Fields employees can update themselves"""
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    bank_account: Optional[str] = None
    bank_sort_code: Optional[str] = None


# ==================== RBAC MODELS ====================

class Permission(BaseModel):
    """Individual permission"""
    name: str
    description: str
    resource: str  # employees, payroll, leave, documents, etc.
    action: str  # create, read, update, delete, approve


class Role(BaseModel):
    """Custom role with permissions"""
    model_config = ConfigDict(extra="ignore")
    role_id: str
    company_id: str
    name: str
    description: str
    permissions: List[str] = []  # List of permission names
    is_system: bool = False  # True for built-in roles
    created_at: datetime


# Default permissions by role
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.OWNER: ["*"],  # All permissions
    UserRole.ADMIN: ["*"],
    UserRole.HR_MANAGER: [
        "employees:*", "leave:*", "documents:*", 
        "scheduling:*", "compliance:read"
    ],
    UserRole.PAYROLL_ADMIN: [
        "employees:read", "payroll:*", "compliance:read"
    ],
    UserRole.MANAGER: [
        "employees:read", "leave:approve", "scheduling:*", 
        "timesheets:approve"
    ],
    UserRole.EMPLOYEE: [
        "self:*", "leave:create", "leave:read_own", 
        "payslips:read_own", "documents:read_own"
    ]
}
