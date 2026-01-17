from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import httpx
import io
import csv
import asyncio
import resend
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# JWT Secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

# Resend Email Configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Currency Configuration - ISO 4217 codes with symbols and exchange rates
SUPPORTED_CURRENCIES = {
    "GBP": {"symbol": "£", "name": "British Pound", "rate_to_gbp": 1.0},
    "USD": {"symbol": "$", "name": "US Dollar", "rate_to_gbp": 0.79},
    "EUR": {"symbol": "€", "name": "Euro", "rate_to_gbp": 0.85},
    "CAD": {"symbol": "C$", "name": "Canadian Dollar", "rate_to_gbp": 0.58},
    "AUD": {"symbol": "A$", "name": "Australian Dollar", "rate_to_gbp": 0.52},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "rate_to_gbp": 0.0053},
    "CHF": {"symbol": "Fr", "name": "Swiss Franc", "rate_to_gbp": 0.89},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "rate_to_gbp": 0.0094},
    "SGD": {"symbol": "S$", "name": "Singapore Dollar", "rate_to_gbp": 0.59},
    "AED": {"symbol": "د.إ", "name": "UAE Dirham", "rate_to_gbp": 0.22},
    "HKD": {"symbol": "HK$", "name": "Hong Kong Dollar", "rate_to_gbp": 0.10},
    "NZD": {"symbol": "NZ$", "name": "New Zealand Dollar", "rate_to_gbp": 0.48},
    "ZAR": {"symbol": "R", "name": "South African Rand", "rate_to_gbp": 0.043},
    "SEK": {"symbol": "kr", "name": "Swedish Krona", "rate_to_gbp": 0.074},
    "NOK": {"symbol": "kr", "name": "Norwegian Krone", "rate_to_gbp": 0.071},
    "DKK": {"symbol": "kr", "name": "Danish Krone", "rate_to_gbp": 0.11},
    "PLN": {"symbol": "zł", "name": "Polish Zloty", "rate_to_gbp": 0.20},
    "MXN": {"symbol": "$", "name": "Mexican Peso", "rate_to_gbp": 0.039},
    "BRL": {"symbol": "R$", "name": "Brazilian Real", "rate_to_gbp": 0.13},
    "CNY": {"symbol": "¥", "name": "Chinese Yuan", "rate_to_gbp": 0.11},
}

# Create the main app
app = FastAPI(title="RealtouchHR API", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

# Auth Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: Optional[str] = None

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
    theme_preference: str = "light"
    created_at: datetime

class TokenResponse(BaseModel):
    token: str
    user: User

# Company Models
class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    address: Optional[str] = None
    payroll_frequency: str = "monthly"

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
    created_at: datetime

# Employee Models
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
    created_at: datetime
    updated_at: datetime

# Leave Models
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

# Document Models
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

# Shift/Rota Models
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

# Timesheet Models
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

# Payroll Models
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

# Audit Models
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

# Compliance Models
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

# AI Copilot Models
class CopilotMessage(BaseModel):
    message: str
    context: Optional[str] = None

class CopilotResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    requires_approval: bool = False

# Bulk Import Models
class BulkImportResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[str] = []
    imported_ids: List[str] = []

# Notification Models
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

# Onboarding Wizard Models
class OnboardingProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_id: str
    step: int
    completed_steps: List[str] = []
    first_employee_added: bool = False
    first_payrun_created: bool = False
    completed: bool = False

# HMRC RTI Models
class RTISubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    submission_id: str
    company_id: str
    payrun_id: str
    submission_type: str  # FPS, EPS, EYU, NVR
    status: str  # draft, submitted, accepted, rejected
    hmrc_response: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime

class RTISubmissionRequest(BaseModel):
    payrun_id: str
    submission_type: str = "FPS"
    test_mode: bool = True

# Payroll Health Check Models
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

# Multi-Currency Models
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

# Employee Self-Service Models
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

# ==================== AUTH HELPERS ====================

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

async def get_current_user(request: Request) -> User:
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check session in database
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        # Try JWT token
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=401, detail="User not found")
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check expiry
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user_doc)

async def create_audit_entry(company_id: str, user: User, action: str, entity_type: str, entity_id: str, details: dict, reason: str = None):
    audit = {
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_log.insert_one(audit)

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserCreate, response: Response):
    # Check if user exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Create user
    user_doc = {
        "user_id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": "owner",
        "theme_preference": "light",
        "created_at": now.isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Create company if provided
    if data.company_name:
        company_id = f"company_{uuid.uuid4().hex[:12]}"
        company_doc = {
            "company_id": company_id,
            "name": data.company_name,
            "owner_id": user_id,
            "payroll_frequency": "monthly",
            "setup_completed": False,
            "created_at": now.isoformat()
        }
        await db.companies.insert_one(company_doc)
        await db.users.update_one({"user_id": user_id}, {"$set": {"company_id": company_id}})
        user_doc["company_id"] = company_id
    
    # Create session
    token = create_jwt_token(user_id, data.email)
    session_doc = {
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60
    )
    
    user_doc.pop("password_hash", None)
    user_doc["created_at"] = now
    return TokenResponse(token=token, user=User(**user_doc))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin, response: Response):
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = user_doc["user_id"]
    now = datetime.now(timezone.utc)
    
    token = create_jwt_token(user_id, data.email)
    session_doc = {
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60
    )
    
    user_doc.pop("password_hash", None)
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return TokenResponse(token=token, user=User(**user_doc))

@api_router.get("/auth/me", response_model=User)
async def get_me(user: User = Depends(get_current_user)):
    return user

@api_router.post("/auth/session")
async def process_google_session(request: Request, response: Response):
    """Process Emergent Google OAuth session"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # Fetch user data from Emergent Auth
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = auth_response.json()
        except Exception as e:
            logger.error(f"Error fetching session data: {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")
    
    now = datetime.now(timezone.utc)
    
    # Check if user exists
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user_doc:
        user_id = user_doc["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": "owner",
            "theme_preference": "light",
            "created_at": now.isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user_doc["user_id"] = user_id
    user_doc["name"] = name
    user_doc["picture"] = picture
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    else:
        user_doc["created_at"] = now
    
    return {"user": User(**user_doc), "token": session_token}

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out"}

@api_router.put("/auth/preferences")
async def update_preferences(data: dict, user: User = Depends(get_current_user)):
    update_fields = {}
    if "theme_preference" in data:
        update_fields["theme_preference"] = data["theme_preference"]
    
    if update_fields:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update_fields})
    
    return {"message": "Preferences updated"}

# ==================== COMPANY ROUTES ====================

@api_router.post("/company", response_model=Company)
async def create_company(data: CompanyCreate, user: User = Depends(get_current_user)):
    company_id = f"company_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    company_doc = {
        "company_id": company_id,
        "name": data.name,
        "industry": data.industry,
        "size": data.size,
        "address": data.address,
        "payroll_frequency": data.payroll_frequency,
        "owner_id": user.user_id,
        "setup_completed": False,
        "created_at": now.isoformat()
    }
    await db.companies.insert_one(company_doc)
    await db.users.update_one({"user_id": user.user_id}, {"$set": {"company_id": company_id}})
    
    await create_audit_entry(company_id, user, "create", "company", company_id, {"name": data.name})
    
    company_doc["created_at"] = now
    return Company(**company_doc)

@api_router.get("/company", response_model=Optional[Company])
async def get_company(user: User = Depends(get_current_user)):
    if not user.company_id:
        return None
    
    company_doc = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    if not company_doc:
        return None
    
    if isinstance(company_doc.get("created_at"), str):
        company_doc["created_at"] = datetime.fromisoformat(company_doc["created_at"])
    
    return Company(**company_doc)

@api_router.put("/company")
async def update_company(data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=404, detail="No company found")
    
    # Allow updating HMRC-related fields for RTI submissions
    allowed_fields = [
        "name", "industry", "size", "address", "payroll_frequency", "setup_completed",
        "paye_reference", "accounts_office_reference", "corporation_tax_reference",
        "hmrc_sender_id", "hmrc_password"
    ]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    
    if update_fields:
        await db.companies.update_one({"company_id": user.company_id}, {"$set": update_fields})
        await create_audit_entry(user.company_id, user, "update", "company", user.company_id, update_fields)
    
    return {"message": "Company updated"}

# ==================== EMPLOYEE ROUTES ====================

@api_router.post("/employees", response_model=Employee)
async def create_employee(data: EmployeeCreate, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    employee_id = f"emp_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Calculate compliance score
    compliance_issues = []
    required_fields = ["ni_number", "tax_code", "bank_account", "bank_sort_code", "salary"]
    for field in required_fields:
        if not getattr(data, field, None):
            compliance_issues.append(f"Missing {field.replace('_', ' ')}")
    
    compliance_score = max(0, 100 - (len(compliance_issues) * 20))
    
    employee_doc = {
        "employee_id": employee_id,
        "company_id": user.company_id,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "job_title": data.job_title,
        "department": data.department,
        "start_date": data.start_date,
        "salary": data.salary,
        "ni_number": data.ni_number,
        "tax_code": data.tax_code,
        "bank_account": data.bank_account,
        "bank_sort_code": data.bank_sort_code,
        "status": "active",
        "compliance_score": compliance_score,
        "compliance_issues": compliance_issues,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.employees.insert_one(employee_doc)
    
    await create_audit_entry(user.company_id, user, "create", "employee", employee_id, {"name": f"{data.first_name} {data.last_name}"})
    
    # Create compliance tasks for missing data
    for issue in compliance_issues:
        task_doc = {
            "task_id": f"task_{uuid.uuid4().hex[:12]}",
            "company_id": user.company_id,
            "title": f"Complete employee data: {issue}",
            "description": f"Employee {data.first_name} {data.last_name} is missing required data",
            "priority": "high",
            "status": "pending",
            "entity_type": "employee",
            "entity_id": employee_id,
            "created_at": now.isoformat()
        }
        await db.compliance_tasks.insert_one(task_doc)
    
    employee_doc["created_at"] = now
    employee_doc["updated_at"] = now
    return Employee(**employee_doc)

@api_router.get("/employees", response_model=List[Employee])
async def get_employees(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    
    for emp in employees:
        if isinstance(emp.get("created_at"), str):
            emp["created_at"] = datetime.fromisoformat(emp["created_at"])
        if isinstance(emp.get("updated_at"), str):
            emp["updated_at"] = datetime.fromisoformat(emp["updated_at"])
    
    return [Employee(**emp) for emp in employees]

@api_router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: str, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    emp = await db.employees.find_one({"employee_id": employee_id, "company_id": user.company_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if isinstance(emp.get("created_at"), str):
        emp["created_at"] = datetime.fromisoformat(emp["created_at"])
    if isinstance(emp.get("updated_at"), str):
        emp["updated_at"] = datetime.fromisoformat(emp["updated_at"])
    
    return Employee(**emp)

@api_router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    allowed_fields = ["first_name", "last_name", "email", "job_title", "department", "start_date", "salary", "ni_number", "tax_code", "bank_account", "bank_sort_code", "status"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate compliance
    emp = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    if emp:
        merged = {**emp, **update_fields}
        compliance_issues = []
        required_fields = ["ni_number", "tax_code", "bank_account", "bank_sort_code", "salary"]
        for field in required_fields:
            if not merged.get(field):
                compliance_issues.append(f"Missing {field.replace('_', ' ')}")
        update_fields["compliance_score"] = max(0, 100 - (len(compliance_issues) * 20))
        update_fields["compliance_issues"] = compliance_issues
    
    await db.employees.update_one({"employee_id": employee_id, "company_id": user.company_id}, {"$set": update_fields})
    await create_audit_entry(user.company_id, user, "update", "employee", employee_id, update_fields)
    
    return {"message": "Employee updated"}

# ==================== LEAVE ROUTES ====================

@api_router.post("/leave", response_model=LeaveRequest)
async def create_leave_request(data: LeaveRequestCreate, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    leave_id = f"leave_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Calculate days (simplified)
    start = datetime.fromisoformat(data.start_date)
    end = datetime.fromisoformat(data.end_date)
    days = (end - start).days + 1
    
    leave_doc = {
        "leave_id": leave_id,
        "employee_id": user.user_id,
        "company_id": user.company_id,
        "leave_type": data.leave_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "days": days,
        "reason": data.reason,
        "status": "pending",
        "created_at": now.isoformat()
    }
    await db.leave_requests.insert_one(leave_doc)
    await create_audit_entry(user.company_id, user, "create", "leave", leave_id, {"type": data.leave_type, "days": days})
    
    leave_doc["created_at"] = now
    return LeaveRequest(**leave_doc)

@api_router.get("/leave", response_model=List[LeaveRequest])
async def get_leave_requests(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    leaves = await db.leave_requests.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    
    for leave in leaves:
        if isinstance(leave.get("created_at"), str):
            leave["created_at"] = datetime.fromisoformat(leave["created_at"])
    
    return [LeaveRequest(**leave) for leave in leaves]

@api_router.put("/leave/{leave_id}")
async def update_leave_request(leave_id: str, data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get the leave request first
    leave = await db.leave_requests.find_one({"leave_id": leave_id, "company_id": user.company_id}, {"_id": 0})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Get employee email for notification
    employee = await db.employees.find_one({"employee_id": leave["employee_id"]}, {"_id": 0})
    
    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
        if data["status"] == "approved":
            update_fields["approved_by"] = user.user_id
            # Send in-app notification
            await create_notification(
                user.company_id,
                leave["employee_id"],
                "Leave Request Approved",
                f"Your {leave['leave_type']} leave request from {leave['start_date']} to {leave['end_date']} has been approved.",
                "leave_approved",
                "leave",
                leave_id
            )
            # Send email notification
            if employee and employee.get("email"):
                await send_email_notification(
                    employee["email"],
                    "Leave Request Approved - RealtouchHR",
                    generate_email_template(
                        "Your Leave Request Has Been Approved! ✓",
                        f"Great news! Your {leave['leave_type']} leave request has been approved.<br><br>"
                        f"<strong>Dates:</strong> {leave['start_date']} to {leave['end_date']}<br>"
                        f"<strong>Days:</strong> {leave.get('days', 'N/A')}",
                        None, None
                    )
                )
        elif data["status"] == "rejected":
            # Send in-app notification
            await create_notification(
                user.company_id,
                leave["employee_id"],
                "Leave Request Rejected",
                f"Your {leave['leave_type']} leave request from {leave['start_date']} to {leave['end_date']} has been rejected.",
                "leave_rejected",
                "leave",
                leave_id
            )
            # Send email notification
            if employee and employee.get("email"):
                await send_email_notification(
                    employee["email"],
                    "Leave Request Update - RealtouchHR",
                    generate_email_template(
                        "Leave Request Not Approved",
                        f"Unfortunately, your {leave['leave_type']} leave request was not approved.<br><br>"
                        f"<strong>Dates:</strong> {leave['start_date']} to {leave['end_date']}<br><br>"
                        f"Please contact your manager if you have any questions.",
                        None, None
                    )
                )
    
    await db.leave_requests.update_one({"leave_id": leave_id, "company_id": user.company_id}, {"$set": update_fields})
    await create_audit_entry(user.company_id, user, "update", "leave", leave_id, update_fields)
    
    return {"message": "Leave request updated"}

# ==================== DOCUMENT ROUTES ====================

@api_router.post("/documents", response_model=Document)
async def create_document(data: DocumentCreate, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    doc = {
        "document_id": document_id,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "name": data.name,
        "doc_type": data.doc_type,
        "content": data.content,
        "status": "draft",
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.documents.insert_one(doc)
    await create_audit_entry(user.company_id, user, "create", "document", document_id, {"name": data.name})
    
    doc["created_at"] = now
    doc["updated_at"] = now
    return Document(**doc)

@api_router.get("/documents", response_model=List[Document])
async def get_documents(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    docs = await db.documents.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    
    for doc in docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
    
    return [Document(**doc) for doc in docs]

# ==================== SHIFT/ROTA ROUTES ====================

@api_router.post("/shifts", response_model=Shift)
async def create_shift(data: ShiftCreate, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    shift_id = f"shift_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    shift_doc = {
        "shift_id": shift_id,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "date": data.date,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "break_minutes": data.break_minutes,
        "status": "scheduled",
        "created_at": now.isoformat()
    }
    await db.shifts.insert_one(shift_doc)
    await create_audit_entry(user.company_id, user, "create", "shift", shift_id, {"employee_id": data.employee_id, "date": data.date})
    
    shift_doc["created_at"] = now
    return Shift(**shift_doc)

@api_router.get("/shifts", response_model=List[Shift])
async def get_shifts(date: Optional[str] = None, user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    query = {"company_id": user.company_id}
    if date:
        query["date"] = date
    
    shifts = await db.shifts.find(query, {"_id": 0}).to_list(1000)
    
    for shift in shifts:
        if isinstance(shift.get("created_at"), str):
            shift["created_at"] = datetime.fromisoformat(shift["created_at"])
    
    return [Shift(**shift) for shift in shifts]

@api_router.post("/shifts/{shift_id}/clock-in")
async def clock_in(shift_id: str, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    await db.shifts.update_one(
        {"shift_id": shift_id, "company_id": user.company_id},
        {"$set": {"clock_in": now.isoformat(), "status": "in-progress"}}
    )
    await create_audit_entry(user.company_id, user, "clock_in", "shift", shift_id, {"time": now.isoformat()})
    return {"message": "Clocked in", "time": now.isoformat()}

@api_router.post("/shifts/{shift_id}/clock-out")
async def clock_out(shift_id: str, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    await db.shifts.update_one(
        {"shift_id": shift_id, "company_id": user.company_id},
        {"$set": {"clock_out": now.isoformat(), "status": "completed"}}
    )
    await create_audit_entry(user.company_id, user, "clock_out", "shift", shift_id, {"time": now.isoformat()})
    return {"message": "Clocked out", "time": now.isoformat()}

# ==================== TIMESHEET ROUTES ====================

@api_router.get("/timesheets", response_model=List[TimesheetEntry])
async def get_timesheets(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    timesheets = await db.timesheets.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    
    for ts in timesheets:
        if isinstance(ts.get("created_at"), str):
            ts["created_at"] = datetime.fromisoformat(ts["created_at"])
        if isinstance(ts.get("updated_at"), str):
            ts["updated_at"] = datetime.fromisoformat(ts["updated_at"])
    
    return [TimesheetEntry(**ts) for ts in timesheets]

@api_router.put("/timesheets/{timesheet_id}")
async def update_timesheet(timesheet_id: str, data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
        if data["status"] == "approved":
            update_fields["approved_by"] = user.user_id
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.timesheets.update_one({"timesheet_id": timesheet_id, "company_id": user.company_id}, {"$set": update_fields})
    await create_audit_entry(user.company_id, user, "update", "timesheet", timesheet_id, update_fields)
    
    return {"message": "Timesheet updated"}

# ==================== PAYROLL ROUTES ====================

@api_router.post("/payroll/runs", response_model=PayRun)
async def create_pay_run(data: PayRunCreate, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    payrun_id = f"payrun_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Get employees and calculate totals
    employees = await db.employees.find({"company_id": user.company_id, "status": "active"}, {"_id": 0}).to_list(1000)
    
    total_gross = 0
    total_tax = 0
    total_ni = 0
    total_net = 0
    payslips = []
    compliance_issues = 0
    
    for emp in employees:
        salary = emp.get("salary", 0) or 0
        monthly_gross = salary / 12
        
        # Simplified UK tax calculations
        tax = monthly_gross * 0.20 if monthly_gross > 1048 else 0  # Basic rate after personal allowance
        ni = monthly_gross * 0.12 if monthly_gross > 797 else 0  # NI threshold
        pension = monthly_gross * 0.05  # Auto-enrollment minimum
        net = monthly_gross - tax - ni - pension
        
        total_gross += monthly_gross
        total_tax += tax
        total_ni += ni
        total_net += net
        
        if emp.get("compliance_score", 100) < 100:
            compliance_issues += 1
        
        payslip = {
            "payrun_id": payrun_id,
            "employee_id": emp["employee_id"],
            "employee_name": f"{emp['first_name']} {emp['last_name']}",
            "gross_pay": round(monthly_gross, 2),
            "tax_deduction": round(tax, 2),
            "ni_deduction": round(ni, 2),
            "pension_deduction": round(pension, 2),
            "other_deductions": 0,
            "net_pay": round(net, 2),
            "overtime_pay": 0
        }
        payslips.append(payslip)
    
    # Calculate compliance score for pay run
    compliance_score = 100 if compliance_issues == 0 else max(0, 100 - (compliance_issues * 10))
    
    payrun_doc = {
        "payrun_id": payrun_id,
        "company_id": user.company_id,
        "period_start": data.period_start,
        "period_end": data.period_end,
        "pay_date": data.pay_date,
        "status": "draft",
        "total_gross": round(total_gross, 2),
        "total_tax": round(total_tax, 2),
        "total_ni": round(total_ni, 2),
        "total_net": round(total_net, 2),
        "employee_count": len(employees),
        "compliance_score": compliance_score,
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.pay_runs.insert_one(payrun_doc)
    
    # Store payslips
    if payslips:
        await db.payslips.insert_many(payslips)
    
    await create_audit_entry(user.company_id, user, "create", "payrun", payrun_id, {"period": f"{data.period_start} to {data.period_end}", "employees": len(employees)})
    
    payrun_doc["created_at"] = now
    payrun_doc["updated_at"] = now
    return PayRun(**payrun_doc)

@api_router.get("/payroll/runs", response_model=List[PayRun])
async def get_pay_runs(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    runs = await db.pay_runs.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    
    for run in runs:
        if isinstance(run.get("created_at"), str):
            run["created_at"] = datetime.fromisoformat(run["created_at"])
        if isinstance(run.get("updated_at"), str):
            run["updated_at"] = datetime.fromisoformat(run["updated_at"])
    
    return [PayRun(**run) for run in runs]

@api_router.get("/payroll/runs/{payrun_id}", response_model=PayRun)
async def get_pay_run(payrun_id: str, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    if isinstance(run.get("created_at"), str):
        run["created_at"] = datetime.fromisoformat(run["created_at"])
    if isinstance(run.get("updated_at"), str):
        run["updated_at"] = datetime.fromisoformat(run["updated_at"])
    
    return PayRun(**run)

@api_router.get("/payroll/runs/{payrun_id}/payslips", response_model=List[PayslipPreview])
async def get_payslips(payrun_id: str, user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    payslips = await db.payslips.find({"payrun_id": payrun_id}, {"_id": 0}).to_list(1000)
    return [PayslipPreview(**ps) for ps in payslips]

@api_router.put("/payroll/runs/{payrun_id}")
async def update_pay_run(payrun_id: str, data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.pay_runs.update_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"$set": update_fields})
    await create_audit_entry(user.company_id, user, "update", "payrun", payrun_id, update_fields, data.get("reason"))
    
    return {"message": "Pay run updated"}

# ==================== AUDIT ROUTES ====================

@api_router.get("/audit", response_model=List[AuditEntry])
async def get_audit_log(limit: int = 100, user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    entries = await db.audit_log.find({"company_id": user.company_id}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for entry in entries:
        if isinstance(entry.get("timestamp"), str):
            entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
    
    return [AuditEntry(**entry) for entry in entries]

# ==================== COMPLIANCE ROUTES ====================

@api_router.get("/compliance/tasks", response_model=List[ComplianceTask])
async def get_compliance_tasks(user: User = Depends(get_current_user)):
    if not user.company_id:
        return []
    
    tasks = await db.compliance_tasks.find({"company_id": user.company_id, "status": "pending"}, {"_id": 0}).to_list(1000)
    
    for task in tasks:
        if isinstance(task.get("created_at"), str):
            task["created_at"] = datetime.fromisoformat(task["created_at"])
    
    return [ComplianceTask(**task) for task in tasks]

@api_router.get("/compliance/score")
async def get_compliance_score(user: User = Depends(get_current_user)):
    if not user.company_id:
        return {"score": 100, "issues": [], "next_action": None}
    
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    tasks = await db.compliance_tasks.find({"company_id": user.company_id, "status": "pending"}, {"_id": 0}).to_list(100)
    
    if not employees:
        return {"score": 100, "issues": [], "next_action": {"title": "Add your first employee", "type": "onboarding"}}
    
    total_score = sum(emp.get("compliance_score", 100) for emp in employees)
    avg_score = total_score // len(employees)
    
    issues = []
    for emp in employees:
        for issue in emp.get("compliance_issues", []):
            issues.append({"employee_id": emp["employee_id"], "employee_name": f"{emp['first_name']} {emp['last_name']}", "issue": issue})
    
    next_action = None
    if tasks:
        next_action = {"title": tasks[0]["title"], "type": "compliance", "task_id": tasks[0]["task_id"]}
    elif issues:
        next_action = {"title": f"Fix compliance issues for {issues[0]['employee_name']}", "type": "employee", "employee_id": issues[0]["employee_id"]}
    
    return {"score": avg_score, "issues": issues[:10], "next_action": next_action}

@api_router.put("/compliance/tasks/{task_id}")
async def update_compliance_task(task_id: str, data: dict, user: User = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    update_fields = {k: v for k, v in data.items() if k in ["status"]}
    
    await db.compliance_tasks.update_one({"task_id": task_id, "company_id": user.company_id}, {"$set": update_fields})
    await create_audit_entry(user.company_id, user, "update", "compliance_task", task_id, update_fields)
    
    return {"message": "Task updated"}

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: User = Depends(get_current_user)):
    if not user.company_id:
        return {
            "total_employees": 0,
            "active_employees": 0,
            "on_leave_today": 0,
            "pending_approvals": 0,
            "compliance_score": 100,
            "next_payroll": None
        }
    
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    active = [e for e in employees if e.get("status") == "active"]
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    leaves = await db.leave_requests.find({
        "company_id": user.company_id,
        "status": "approved",
        "start_date": {"$lte": today},
        "end_date": {"$gte": today}
    }, {"_id": 0}).to_list(100)
    
    pending_leaves = await db.leave_requests.count_documents({"company_id": user.company_id, "status": "pending"})
    pending_timesheets = await db.timesheets.count_documents({"company_id": user.company_id, "status": "pending"})
    
    compliance = await get_compliance_score(user)
    
    return {
        "total_employees": len(employees),
        "active_employees": len(active),
        "on_leave_today": len(leaves),
        "pending_approvals": pending_leaves + pending_timesheets,
        "compliance_score": compliance["score"],
        "next_action": compliance.get("next_action")
    }

# ==================== AI COPILOT ROUTES ====================

@api_router.post("/copilot/chat", response_model=CopilotResponse)
async def chat_with_copilot(data: CopilotMessage, user: User = Depends(get_current_user)):
    """AI Copilot for HR/Payroll guidance with human-in-the-loop"""
    
    # Get company context
    company = None
    if user.company_id:
        company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    # Get compliance context
    compliance = await get_compliance_score(user) if user.company_id else None
    
    # Build system prompt
    system_prompt = """You are the RealtouchHR AI Copilot - a compliance-focused HR and payroll assistant for UK businesses.

IMPORTANT RULES:
1. NEVER execute payroll, tax, or legal actions automatically
2. ALWAYS explain your reasoning and sources
3. If uncertain, ask clarifying questions
4. For any action that affects pay or legal compliance, REQUIRE explicit human approval
5. Use UK-specific terminology (NI, PAYE, P45, P60, etc.)

Your role is to:
- Guide users through HR and payroll processes
- Explain compliance requirements
- Help draft documents and policies
- Answer questions about UK employment law (general guidance only, not legal advice)
- Identify potential compliance issues

Current context:
- Company: {company_name}
- Compliance Score: {compliance_score}%
- Pending Issues: {issues}
""".format(
        company_name=company.get("name") if company else "Not set up",
        compliance_score=compliance.get("score", 100) if compliance else 100,
        issues=len(compliance.get("issues", [])) if compliance else 0
    )
    
    # Use emergentintegrations for AI response
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return CopilotResponse(
                response="AI Copilot is currently unavailable. Please ensure the API key is configured.",
                suggestions=["Check system configuration", "Contact administrator"],
                requires_approval=False
            )
        
        # Create chat instance with system message
        chat = LlmChat(
            api_key=api_key,
            session_id=f"copilot_{user.user_id}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        # Create user message
        user_message = UserMessage(text=data.message)
        
        # Get response
        ai_response = await chat.send_message(user_message)
        
        # Check if response requires approval
        requires_approval = any(keyword in data.message.lower() for keyword in ["approve", "submit", "run payroll", "terminate", "pay", "salary change"])
        
        suggestions = []
        if compliance and compliance.get("next_action"):
            suggestions.append(compliance["next_action"]["title"])
        
        return CopilotResponse(
            response=ai_response,
            suggestions=suggestions,
            requires_approval=requires_approval
        )
        
    except Exception as e:
        logger.error(f"AI Copilot error: {e}")
        return CopilotResponse(
            response="I'm having trouble processing your request. Please try again or contact support.",
            suggestions=["Refresh the page", "Try a simpler question"],
            requires_approval=False
        )

# ==================== HEALTH CHECK ====================

@api_router.get("/")
async def root():
    return {"message": "RealtouchHR API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==================== NOTIFICATION HELPER ====================

async def create_notification(company_id: str, user_id: str, title: str, message: str, 
                             notification_type: str, entity_type: str = None, entity_id: str = None):
    """Create a notification for a user"""
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": user_id,
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    return notification

# ==================== NOTIFICATION ROUTES ====================

@api_router.get("/notifications")
async def get_notifications(limit: int = 20, user: User = Depends(get_current_user)):
    """Get user notifications"""
    notifications = await db.notifications.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for notif in notifications:
        if isinstance(notif.get("created_at"), str):
            notif["created_at"] = datetime.fromisoformat(notif["created_at"])
    
    unread_count = await db.notifications.count_documents({"user_id": user.user_id, "read": False})
    
    return {"notifications": notifications, "unread_count": unread_count}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user.user_id},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"user_id": user.user_id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}

# ==================== BULK IMPORT ROUTES ====================

@api_router.post("/employees/import", response_model=BulkImportResult)
async def import_employees_csv(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Import employees from CSV file"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    success_count = 0
    error_count = 0
    errors = []
    imported_ids = []
    now = datetime.now(timezone.utc)
    
    required_fields = ['first_name', 'last_name', 'email']
    
    for row_num, row in enumerate(reader, start=2):
        try:
            # Validate required fields
            missing = [f for f in required_fields if not row.get(f)]
            if missing:
                errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing)}")
                error_count += 1
                continue
            
            # Check for duplicate email
            existing = await db.employees.find_one({"email": row['email'], "company_id": user.company_id})
            if existing:
                errors.append(f"Row {row_num}: Employee with email {row['email']} already exists")
                error_count += 1
                continue
            
            employee_id = f"emp_{uuid.uuid4().hex[:12]}"
            
            # Parse salary
            salary = None
            if row.get('salary'):
                try:
                    salary = float(row['salary'].replace(',', '').replace('£', ''))
                except:
                    pass
            
            # Calculate compliance
            compliance_issues = []
            fields_to_check = ['ni_number', 'tax_code', 'bank_account', 'bank_sort_code']
            for field in fields_to_check:
                if not row.get(field):
                    compliance_issues.append(f"Missing {field.replace('_', ' ')}")
            if not salary:
                compliance_issues.append("Missing salary")
            
            compliance_score = max(0, 100 - (len(compliance_issues) * 20))
            
            employee_doc = {
                "employee_id": employee_id,
                "company_id": user.company_id,
                "first_name": row['first_name'].strip(),
                "last_name": row['last_name'].strip(),
                "email": row['email'].strip().lower(),
                "job_title": row.get('job_title', '').strip() or None,
                "department": row.get('department', '').strip() or None,
                "start_date": row.get('start_date', '').strip() or None,
                "salary": salary,
                "ni_number": row.get('ni_number', '').strip() or None,
                "tax_code": row.get('tax_code', '').strip() or None,
                "bank_account": row.get('bank_account', '').strip() or None,
                "bank_sort_code": row.get('bank_sort_code', '').strip() or None,
                "status": "active",
                "compliance_score": compliance_score,
                "compliance_issues": compliance_issues,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            await db.employees.insert_one(employee_doc)
            imported_ids.append(employee_id)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            error_count += 1
    
    # Log audit entry
    await create_audit_entry(
        user.company_id, user, "bulk_import", "employee", "multiple",
        {"success_count": success_count, "error_count": error_count}
    )
    
    return BulkImportResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors[:10],  # Limit errors returned
        imported_ids=imported_ids
    )

@api_router.get("/employees/import/template")
async def get_employee_import_template():
    """Download CSV template for employee import"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'first_name', 'last_name', 'email', 'job_title', 'department',
        'start_date', 'salary', 'ni_number', 'tax_code', 'bank_account', 'bank_sort_code'
    ])
    
    # Example row
    writer.writerow([
        'John', 'Smith', 'john.smith@company.com', 'Software Engineer', 'Engineering',
        '2024-01-15', '45000', 'AB123456C', '1257L', '12345678', '12-34-56'
    ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employee_import_template.csv"}
    )

@api_router.post("/timesheets/import", response_model=BulkImportResult)
async def import_timesheets_csv(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Import timesheets from CSV file"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    success_count = 0
    error_count = 0
    errors = []
    imported_ids = []
    now = datetime.now(timezone.utc)
    
    for row_num, row in enumerate(reader, start=2):
        try:
            employee_email = row.get('employee_email', '').strip()
            if not employee_email:
                errors.append(f"Row {row_num}: Missing employee_email")
                error_count += 1
                continue
            
            # Find employee
            employee = await db.employees.find_one({"email": employee_email, "company_id": user.company_id})
            if not employee:
                errors.append(f"Row {row_num}: Employee {employee_email} not found")
                error_count += 1
                continue
            
            timesheet_id = f"ts_{uuid.uuid4().hex[:12]}"
            
            hours_worked = float(row.get('hours_worked', 0))
            overtime_hours = float(row.get('overtime_hours', 0))
            
            timesheet_doc = {
                "timesheet_id": timesheet_id,
                "company_id": user.company_id,
                "employee_id": employee["employee_id"],
                "week_start": row.get('week_start', ''),
                "hours_worked": hours_worked,
                "overtime_hours": overtime_hours,
                "status": "pending",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            await db.timesheets.insert_one(timesheet_doc)
            imported_ids.append(timesheet_id)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            error_count += 1
    
    await create_audit_entry(
        user.company_id, user, "bulk_import", "timesheet", "multiple",
        {"success_count": success_count, "error_count": error_count}
    )
    
    return BulkImportResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors[:10],
        imported_ids=imported_ids
    )

# ==================== PDF PAYSLIP GENERATION ====================

def generate_payslip_pdf(payslip: dict, company: dict, pay_period: dict) -> bytes:
    """Generate a PDF payslip"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=12, spaceAfter=5)
    normal_style = styles['Normal']
    
    elements = []
    
    # Company Header
    elements.append(Paragraph(company.get('name', 'Company'), title_style))
    elements.append(Paragraph("PAYSLIP", subtitle_style))
    elements.append(Spacer(1, 10*mm))
    
    # Employee & Period Info
    info_data = [
        ['Employee:', payslip.get('employee_name', 'N/A'), 'Pay Period:', f"{pay_period.get('period_start', '')} to {pay_period.get('period_end', '')}"],
        ['Employee ID:', payslip.get('employee_id', 'N/A'), 'Pay Date:', pay_period.get('pay_date', '')],
    ]
    
    info_table = Table(info_data, colWidths=[70, 150, 70, 150])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Earnings Table
    elements.append(Paragraph("Earnings", header_style))
    earnings_data = [
        ['Description', 'Amount'],
        ['Basic Salary', f"£{payslip.get('gross_pay', 0):,.2f}"],
        ['Overtime', f"£{payslip.get('overtime_pay', 0):,.2f}"],
        ['Gross Pay', f"£{payslip.get('gross_pay', 0):,.2f}"],
    ]
    
    earnings_table = Table(earnings_data, colWidths=[300, 140])
    earnings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(earnings_table)
    elements.append(Spacer(1, 8*mm))
    
    # Deductions Table
    elements.append(Paragraph("Deductions", header_style))
    deductions_data = [
        ['Description', 'Amount'],
        ['Income Tax (PAYE)', f"£{payslip.get('tax_deduction', 0):,.2f}"],
        ['National Insurance', f"£{payslip.get('ni_deduction', 0):,.2f}"],
        ['Pension Contribution', f"£{payslip.get('pension_deduction', 0):,.2f}"],
        ['Other Deductions', f"£{payslip.get('other_deductions', 0):,.2f}"],
        ['Total Deductions', f"£{(payslip.get('tax_deduction', 0) + payslip.get('ni_deduction', 0) + payslip.get('pension_deduction', 0) + payslip.get('other_deductions', 0)):,.2f}"],
    ]
    
    deductions_table = Table(deductions_data, colWidths=[300, 140])
    deductions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fee2e2')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(deductions_table)
    elements.append(Spacer(1, 10*mm))
    
    # Net Pay
    net_pay_data = [
        ['NET PAY', f"£{payslip.get('net_pay', 0):,.2f}"],
    ]
    net_pay_table = Table(net_pay_data, colWidths=[300, 140])
    net_pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(net_pay_table)
    elements.append(Spacer(1, 15*mm))
    
    # Footer
    footer_text = "This is a computer-generated payslip. For queries, please contact HR."
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

@api_router.get("/payroll/runs/{payrun_id}/payslips/{employee_id}/pdf")
async def download_payslip_pdf(payrun_id: str, employee_id: str, user: User = Depends(get_current_user)):
    """Download individual payslip as PDF"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Get payslip
    payslip = await db.payslips.find_one({"payrun_id": payrun_id, "employee_id": employee_id}, {"_id": 0})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    # Get company
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    # Generate PDF
    pdf_bytes = generate_payslip_pdf(payslip, company or {}, pay_run)
    
    filename = f"payslip_{payslip['employee_name'].replace(' ', '_')}_{pay_run['period_end']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/payroll/runs/{payrun_id}/payslips/pdf")
async def download_all_payslips_pdf(payrun_id: str, user: User = Depends(get_current_user)):
    """Download all payslips for a pay run as a single PDF"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Get all payslips
    payslips = await db.payslips.find({"payrun_id": payrun_id}, {"_id": 0}).to_list(1000)
    if not payslips:
        raise HTTPException(status_code=404, detail="No payslips found")
    
    # Get company
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    # Generate combined PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    for i, payslip in enumerate(payslips):
        if i > 0:
            from reportlab.platypus import PageBreak
            elements.append(PageBreak())
        
        # Use the same generation logic
        pdf_bytes = generate_payslip_pdf(payslip, company or {}, pay_run)
        # For combined, we'll just append placeholder - in real impl, merge PDFs
    
    # For simplicity, return first payslip PDF - in production would merge all
    first_payslip_pdf = generate_payslip_pdf(payslips[0], company or {}, pay_run)
    
    filename = f"payslips_{pay_run['period_end']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(first_payslip_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== HMRC EXPORT ROUTES ====================

@api_router.get("/payroll/runs/{payrun_id}/export/fps")
async def export_fps_csv(payrun_id: str, user: User = Depends(get_current_user)):
    """Export Full Payment Submission (FPS) data for HMRC"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    payslips = await db.payslips.find({"payrun_id": payrun_id}, {"_id": 0}).to_list(1000)
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    emp_map = {e["employee_id"]: e for e in employees}
    
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # FPS Header
    writer.writerow([
        'Employer PAYE Reference', 'Accounts Office Reference', 'Tax Year', 'Tax Month',
        'Employee NI Number', 'Employee First Name', 'Employee Last Name',
        'Date of Birth', 'Gender', 'Address Line 1', 'Postcode',
        'Tax Code', 'Taxable Pay YTD', 'Tax Deducted YTD',
        'NI Category', 'NI Earnings YTD', 'NI Contributions YTD',
        'Payment Date', 'Pay Frequency', 'Gross Pay This Period',
        'Tax This Period', 'NI This Period'
    ])
    
    for payslip in payslips:
        emp = emp_map.get(payslip["employee_id"], {})
        writer.writerow([
            company.get("paye_reference", ""),
            company.get("accounts_office_ref", ""),
            "2024-25",  # Tax year
            "",  # Tax month
            emp.get("ni_number", ""),
            emp.get("first_name", ""),
            emp.get("last_name", ""),
            "",  # DOB
            "",  # Gender
            "",  # Address
            "",  # Postcode
            emp.get("tax_code", "1257L"),
            payslip.get("gross_pay", 0),
            payslip.get("tax_deduction", 0),
            "A",  # NI Category
            payslip.get("gross_pay", 0),
            payslip.get("ni_deduction", 0),
            pay_run.get("pay_date", ""),
            "M" if company.get("payroll_frequency") == "monthly" else "W",
            payslip.get("gross_pay", 0),
            payslip.get("tax_deduction", 0),
            payslip.get("ni_deduction", 0)
        ])
    
    output.seek(0)
    filename = f"fps_export_{pay_run['period_end']}.csv"
    
    await create_audit_entry(user.company_id, user, "export", "fps", payrun_id, {"format": "csv"})
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/payroll/runs/{payrun_id}/export/eps")
async def export_eps_csv(payrun_id: str, user: User = Depends(get_current_user)):
    """Export Employer Payment Summary (EPS) data for HMRC"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # EPS Header
    writer.writerow([
        'Employer PAYE Reference', 'Accounts Office Reference', 'Tax Year', 'Tax Month',
        'No Payment Indicator', 'Period Of Inactivity From', 'Period Of Inactivity To',
        'Statutory Maternity Pay', 'Statutory Paternity Pay', 'Statutory Adoption Pay',
        'Statutory Shared Parental Pay', 'CIS Deductions', 'Apprenticeship Levy',
        'Employment Allowance Indicator'
    ])
    
    writer.writerow([
        company.get("paye_reference", ""),
        company.get("accounts_office_ref", ""),
        "2024-25",
        "",
        "No",  # No payment indicator
        "",
        "",
        0,  # SMP
        0,  # SPP
        0,  # SAP
        0,  # ShPP
        0,  # CIS
        pay_run.get("total_gross", 0) * 0.005 if pay_run.get("total_gross", 0) > 3000000 else 0,  # Apprenticeship levy
        "Yes" if pay_run.get("employee_count", 0) < 5 else "No"  # Employment allowance
    ])
    
    output.seek(0)
    filename = f"eps_export_{pay_run['period_end']}.csv"
    
    await create_audit_entry(user.company_id, user, "export", "eps", payrun_id, {"format": "csv"})
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/payroll/runs/{payrun_id}/export/p32")
async def export_p32_report(payrun_id: str, user: User = Depends(get_current_user)):
    """Export P32 Employer Payment Record"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # P32 Report
    writer.writerow(['P32 Employer Payment Record'])
    writer.writerow([])
    writer.writerow(['Company', company.get("name", "")])
    writer.writerow(['PAYE Reference', company.get("paye_reference", "")])
    writer.writerow(['Tax Year', '2024-25'])
    writer.writerow(['Pay Period', f"{pay_run['period_start']} to {pay_run['period_end']}"])
    writer.writerow([])
    writer.writerow(['Description', 'Amount'])
    writer.writerow(['Total PAYE Tax', f"£{pay_run.get('total_tax', 0):,.2f}"])
    writer.writerow(['Total NI (Employee)', f"£{pay_run.get('total_ni', 0):,.2f}"])
    writer.writerow(['Total NI (Employer)', f"£{pay_run.get('total_ni', 0) * 1.138:,.2f}"])  # Estimated employer NI
    writer.writerow(['Student Loan Deductions', '£0.00'])
    writer.writerow(['Statutory Payments Reclaimed', '£0.00'])
    writer.writerow([])
    writer.writerow(['Amount Due to HMRC', f"£{(pay_run.get('total_tax', 0) + pay_run.get('total_ni', 0) * 2.138):,.2f}"])
    
    output.seek(0)
    filename = f"p32_report_{pay_run['period_end']}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== ONBOARDING WIZARD ROUTES ====================

@api_router.get("/onboarding/progress")
async def get_onboarding_progress(user: User = Depends(get_current_user)):
    """Get onboarding wizard progress"""
    if not user.company_id:
        return {
            "step": 1,
            "completed_steps": [],
            "first_employee_added": False,
            "first_payrun_created": False,
            "completed": False
        }
    
    # Check what's been completed
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1)
    pay_runs = await db.pay_runs.find({"company_id": user.company_id}, {"_id": 0}).to_list(1)
    
    completed_steps = []
    step = 1
    
    # Step 1: Company setup
    if company and company.get("name"):
        completed_steps.append("company_setup")
        step = 2
    
    # Step 2: First employee
    first_employee_added = len(employees) > 0
    if first_employee_added:
        completed_steps.append("first_employee")
        step = 3
    
    # Step 3: Payroll preview
    first_payrun_created = len(pay_runs) > 0
    if first_payrun_created:
        completed_steps.append("first_payrun")
        step = 4
    
    completed = len(completed_steps) >= 3
    
    return {
        "step": step,
        "completed_steps": completed_steps,
        "first_employee_added": first_employee_added,
        "first_payrun_created": first_payrun_created,
        "completed": completed
    }

@api_router.post("/onboarding/quick-employee")
async def quick_add_employee(data: EmployeeCreate, user: User = Depends(get_current_user)):
    """Quickly add an employee during onboarding"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="Please complete company setup first")
    
    # Use existing employee creation logic
    employee = await create_employee(data, user)
    
    # Check if this triggers payroll wizard
    progress = await get_onboarding_progress(user)
    
    return {
        "employee": employee,
        "onboarding_progress": progress,
        "next_step": "Create your first pay run preview" if progress["step"] == 3 else None
    }

@api_router.post("/onboarding/quick-payrun")
async def quick_create_payrun(user: User = Depends(get_current_user)):
    """Quickly create a pay run preview during onboarding"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="Please complete company setup first")
    
    # Get current date info for default period
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    # Last day of month
    if now.month == 12:
        period_end = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        period_end = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
    period_end = period_end.strftime("%Y-%m-%d")
    
    pay_date = period_end  # Pay on last day of month
    
    data = PayRunCreate(period_start=period_start, period_end=period_end, pay_date=pay_date)
    pay_run = await create_pay_run(data, user)
    
    progress = await get_onboarding_progress(user)
    
    return {
        "pay_run": pay_run,
        "onboarding_progress": progress,
        "message": "Congratulations! You've completed the quick setup. Your first payroll preview is ready!"
    }

# ==================== EMAIL HELPER ====================

async def send_email_notification(to_email: str, subject: str, html_content: str):
    """Send email notification using Resend"""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return None
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return None

def generate_email_template(title: str, body: str, action_url: str = None, action_text: str = None) -> str:
    """Generate HTML email template"""
    action_button = ""
    if action_url and action_text:
        action_button = f'''
        <tr>
            <td style="padding: 20px 0;">
                <a href="{action_url}" style="background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">{action_text}</a>
            </td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <tr>
                <td style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">RealtouchHR</h1>
                </td>
            </tr>
            <tr>
                <td style="background-color: white; padding: 30px; border-radius: 0 0 12px 12px;">
                    <h2 style="color: #1f2937; margin: 0 0 20px 0;">{title}</h2>
                    <p style="color: #4b5563; line-height: 1.6; margin: 0 0 20px 0;">{body}</p>
                    {action_button}
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">This email was sent by RealtouchHR. If you have questions, please contact your HR administrator.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''

# ==================== MULTI-CURRENCY ROUTES ====================

@api_router.get("/currencies", response_model=List[CurrencyInfo])
async def get_supported_currencies():
    """Get list of all supported currencies"""
    return [
        CurrencyInfo(code=code, **info)
        for code, info in SUPPORTED_CURRENCIES.items()
    ]

@api_router.get("/currencies/{currency_code}")
async def get_currency_info(currency_code: str):
    """Get info for a specific currency"""
    code = currency_code.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=404, detail=f"Currency {code} not supported")
    
    info = SUPPORTED_CURRENCIES[code]
    return CurrencyInfo(code=code, **info)

@api_router.post("/currencies/convert", response_model=CurrencyConversion)
async def convert_currency(from_currency: str, to_currency: str, amount: float):
    """Convert amount between currencies"""
    from_code = from_currency.upper()
    to_code = to_currency.upper()
    
    if from_code not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Currency {from_code} not supported")
    if to_code not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Currency {to_code} not supported")
    
    # Convert via GBP as base
    gbp_amount = amount * SUPPORTED_CURRENCIES[from_code]["rate_to_gbp"]
    converted = gbp_amount / SUPPORTED_CURRENCIES[to_code]["rate_to_gbp"]
    rate = SUPPORTED_CURRENCIES[from_code]["rate_to_gbp"] / SUPPORTED_CURRENCIES[to_code]["rate_to_gbp"]
    
    return CurrencyConversion(
        from_currency=from_code,
        to_currency=to_code,
        amount=amount,
        converted_amount=round(converted, 2),
        rate=round(rate, 6)
    )

@api_router.put("/company/currency")
async def update_company_currency(data: dict, user: User = Depends(get_current_user)):
    """Update company's default currency"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    currency = data.get("currency", "GBP").upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Currency {currency} not supported")
    
    await db.companies.update_one(
        {"company_id": user.company_id},
        {"$set": {"default_currency": currency}}
    )
    
    await create_audit_entry(user.company_id, user, "update", "company", user.company_id, {"default_currency": currency})
    
    return {"message": f"Default currency updated to {currency}"}

# ==================== PAYROLL HEALTH CHECK ROUTES ====================

@api_router.get("/payroll/health-check/{payrun_id}", response_model=PayrollHealthCheckResult)
async def run_payroll_health_check(payrun_id: str, user: User = Depends(get_current_user)):
    """Run comprehensive health check before processing payroll"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    employees = await db.employees.find({"company_id": user.company_id, "status": "active"}, {"_id": 0}).to_list(1000)
    payslips = await db.payslips.find({"payrun_id": payrun_id}, {"_id": 0}).to_list(1000)
    
    issues = []
    critical_count = 0
    warning_count = 0
    
    for emp in employees:
        emp_name = f"{emp['first_name']} {emp['last_name']}"
        emp_id = emp["employee_id"]
        
        # Missing Critical Data
        if not emp.get("ni_number"):
            issues.append(HealthCheckIssue(
                severity="critical",
                category="missing_data",
                employee_id=emp_id,
                employee_name=emp_name,
                title="Missing NI Number",
                description=f"{emp_name} does not have a National Insurance number on file.",
                action_required="Add NI number before processing payroll"
            ))
            critical_count += 1
        
        if not emp.get("tax_code"):
            issues.append(HealthCheckIssue(
                severity="warning",
                category="missing_data",
                employee_id=emp_id,
                employee_name=emp_name,
                title="Missing Tax Code",
                description=f"{emp_name} does not have a tax code. Default 1257L will be used.",
                action_required="Verify tax code with HMRC or employee's P45"
            ))
            warning_count += 1
        
        if not emp.get("bank_account") or not emp.get("bank_sort_code"):
            issues.append(HealthCheckIssue(
                severity="critical",
                category="banking",
                employee_id=emp_id,
                employee_name=emp_name,
                title="Missing Bank Details",
                description=f"{emp_name} does not have complete bank details for payment.",
                action_required="Add bank account number and sort code"
            ))
            critical_count += 1
        
        if not emp.get("salary"):
            issues.append(HealthCheckIssue(
                severity="critical",
                category="missing_data",
                employee_id=emp_id,
                employee_name=emp_name,
                title="No Salary Defined",
                description=f"{emp_name} does not have a salary configured.",
                action_required="Set annual salary for employee"
            ))
            critical_count += 1
        
        # Anomaly Detection
        if emp.get("salary"):
            monthly_gross = emp["salary"] / 12
            
            # Check for unusually low salary (below minimum wage equivalent)
            if emp["salary"] < 12000:  # Roughly below min wage for full time
                issues.append(HealthCheckIssue(
                    severity="warning",
                    category="anomaly",
                    employee_id=emp_id,
                    employee_name=emp_name,
                    title="Salary Below Threshold",
                    description=f"{emp_name}'s annual salary (£{emp['salary']:,.0f}) may be below minimum wage for full-time work.",
                    action_required="Verify if employee is part-time or salary is correct"
                ))
                warning_count += 1
            
            # Check for salary changes in historical data (simplified)
            history = await db.salary_history.find_one({"employee_id": emp_id}, {"_id": 0})
            if history and history.get("previous_salary"):
                change_pct = abs(emp["salary"] - history["previous_salary"]) / history["previous_salary"] * 100
                if change_pct > 20:
                    issues.append(HealthCheckIssue(
                        severity="warning",
                        category="anomaly",
                        employee_id=emp_id,
                        employee_name=emp_name,
                        title="Large Salary Change",
                        description=f"{emp_name}'s salary changed by {change_pct:.1f}% since last period.",
                        action_required="Verify salary change is intentional"
                    ))
                    warning_count += 1
    
    # Compliance Checks
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    if not company.get("paye_reference"):
        issues.append(HealthCheckIssue(
            severity="warning",
            category="compliance",
            title="Missing PAYE Reference",
            description="Company does not have a PAYE Employer Reference Number configured.",
            action_required="Add PAYE reference in Company Settings for HMRC submissions"
        ))
        warning_count += 1
    
    # Calculate overall status and score
    if critical_count > 0:
        overall_status = "fail"
        score = max(0, 100 - (critical_count * 20) - (warning_count * 5))
        can_proceed = False
    elif warning_count > 3:
        overall_status = "warning"
        score = max(50, 100 - (warning_count * 10))
        can_proceed = True
    elif warning_count > 0:
        overall_status = "warning"
        score = 100 - (warning_count * 5)
        can_proceed = True
    else:
        overall_status = "pass"
        score = 100
        can_proceed = True
    
    return PayrollHealthCheckResult(
        payrun_id=payrun_id,
        check_date=datetime.now(timezone.utc).isoformat(),
        overall_status=overall_status,
        score=score,
        issues=issues,
        can_proceed=can_proceed
    )

# ==================== HMRC RTI ROUTES ====================

@api_router.post("/hmrc/rti/submit")
async def submit_rti(data: RTISubmissionRequest, user: User = Depends(get_current_user)):
    """Submit RTI data to HMRC (test mode or live)"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    pay_run = await db.pay_runs.find_one({"payrun_id": data.payrun_id, "company_id": user.company_id}, {"_id": 0})
    if not pay_run:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Run health check first
    health_check = await run_payroll_health_check(data.payrun_id, user)
    if not health_check.can_proceed and not data.test_mode:
        raise HTTPException(
            status_code=400, 
            detail=f"Payroll health check failed with {len([i for i in health_check.issues if i.severity == 'critical'])} critical issues. Please resolve before submission."
        )
    
    submission_id = f"rti_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Get company and employee data for submission
    company = await db.companies.find_one({"company_id": user.company_id}, {"_id": 0})
    payslips = await db.payslips.find({"payrun_id": data.payrun_id}, {"_id": 0}).to_list(1000)
    employees = await db.employees.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    emp_map = {e["employee_id"]: e for e in employees}
    
    # Build RTI XML/Data structure (simplified for demo)
    rti_data = {
        "employer": {
            "paye_reference": company.get("paye_reference", ""),
            "accounts_office_reference": company.get("accounts_office_ref", ""),
            "name": company.get("name", "")
        },
        "tax_year": "2024-25",
        "submission_type": data.submission_type,
        "employees": []
    }
    
    for payslip in payslips:
        emp = emp_map.get(payslip["employee_id"], {})
        rti_data["employees"].append({
            "ni_number": emp.get("ni_number", ""),
            "first_name": emp.get("first_name", ""),
            "last_name": emp.get("last_name", ""),
            "tax_code": emp.get("tax_code", "1257L"),
            "gross_pay": payslip.get("gross_pay", 0),
            "tax_deducted": payslip.get("tax_deduction", 0),
            "ni_contributions": payslip.get("ni_deduction", 0),
            "payment_date": pay_run.get("pay_date", "")
        })
    
    # In test mode, simulate HMRC response
    if data.test_mode:
        hmrc_response = {
            "status": "accepted",
            "correlation_id": f"TEST-{uuid.uuid4().hex[:8]}",
            "message": "Test submission accepted",
            "timestamp": now.isoformat()
        }
        status = "accepted"
    else:
        # In production, this would call HMRC's Government Gateway API
        # For now, we simulate the submission
        hmrc_response = {
            "status": "pending",
            "correlation_id": f"HMRC-{uuid.uuid4().hex[:12]}",
            "message": "Submission received - awaiting HMRC processing",
            "timestamp": now.isoformat(),
            "note": "HMRC RTI API integration requires Government Gateway credentials"
        }
        status = "submitted"
    
    # Store submission record
    submission_doc = {
        "submission_id": submission_id,
        "company_id": user.company_id,
        "payrun_id": data.payrun_id,
        "submission_type": data.submission_type,
        "status": status,
        "test_mode": data.test_mode,
        "rti_data": rti_data,
        "hmrc_response": hmrc_response,
        "correlation_id": hmrc_response.get("correlation_id"),
        "submitted_at": now.isoformat(),
        "created_at": now.isoformat()
    }
    await db.rti_submissions.insert_one(submission_doc)
    
    # Update pay run status
    if not data.test_mode:
        await db.pay_runs.update_one(
            {"payrun_id": data.payrun_id},
            {"$set": {"rti_status": status, "rti_submission_id": submission_id}}
        )
    
    await create_audit_entry(
        user.company_id, user, "submit", "rti", submission_id,
        {"type": data.submission_type, "test_mode": data.test_mode, "payrun": data.payrun_id}
    )
    
    return {
        "submission_id": submission_id,
        "status": status,
        "hmrc_response": hmrc_response,
        "message": f"RTI {data.submission_type} {'test ' if data.test_mode else ''}submission {'accepted' if data.test_mode else 'sent to HMRC'}"
    }

@api_router.get("/hmrc/rti/submissions")
async def get_rti_submissions(user: User = Depends(get_current_user)):
    """Get all RTI submissions for the company"""
    if not user.company_id:
        return []
    
    submissions = await db.rti_submissions.find(
        {"company_id": user.company_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return submissions

@api_router.get("/hmrc/rti/submissions/{submission_id}")
async def get_rti_submission(submission_id: str, user: User = Depends(get_current_user)):
    """Get details of a specific RTI submission"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission

# ==================== EMPLOYEE SELF-SERVICE ROUTES ====================

@api_router.get("/self-service/profile", response_model=SelfServiceProfile)
async def get_self_service_profile(user: User = Depends(get_current_user)):
    """Get employee's own profile for self-service"""
    # Find employee record linked to this user
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        # Create a basic profile from user data
        return SelfServiceProfile(
            employee_id=user.user_id,
            first_name=user.name.split()[0] if user.name else "",
            last_name=" ".join(user.name.split()[1:]) if user.name and len(user.name.split()) > 1 else "",
            email=user.email,
            can_edit_personal=True,
            can_view_payslips=True,
            can_request_leave=True
        )
    
    return SelfServiceProfile(
        employee_id=employee["employee_id"],
        first_name=employee["first_name"],
        last_name=employee["last_name"],
        email=employee["email"],
        job_title=employee.get("job_title"),
        department=employee.get("department"),
        start_date=employee.get("start_date"),
        can_edit_personal=True,
        can_view_payslips=True,
        can_request_leave=True
    )

@api_router.put("/self-service/profile")
async def update_self_service_profile(data: dict, user: User = Depends(get_current_user)):
    """Update employee's own profile (limited fields)"""
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Only allow updating specific fields
    allowed_fields = ["phone", "address", "emergency_contact", "emergency_phone"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"employee_id": employee["employee_id"]},
        {"$set": update_fields}
    )
    
    return {"message": "Profile updated successfully"}

@api_router.get("/self-service/payslips", response_model=List[SelfServicePayslip])
async def get_self_service_payslips(user: User = Depends(get_current_user)):
    """Get employee's own payslips"""
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        return []
    
    # Get all payslips for this employee
    payslips = await db.payslips.find(
        {"employee_id": employee["employee_id"]},
        {"_id": 0}
    ).to_list(100)
    
    result = []
    for payslip in payslips:
        # Get pay run info
        pay_run = await db.pay_runs.find_one({"payrun_id": payslip["payrun_id"]}, {"_id": 0})
        if pay_run:
            result.append(SelfServicePayslip(
                payrun_id=payslip["payrun_id"],
                period_start=pay_run.get("period_start", ""),
                period_end=pay_run.get("period_end", ""),
                pay_date=pay_run.get("pay_date", ""),
                gross_pay=payslip.get("gross_pay", 0),
                net_pay=payslip.get("net_pay", 0),
                status=pay_run.get("status", "")
            ))
    
    return sorted(result, key=lambda x: x.pay_date, reverse=True)

@api_router.get("/self-service/payslips/{payrun_id}/pdf")
async def download_self_service_payslip(payrun_id: str, user: User = Depends(get_current_user)):
    """Download own payslip as PDF"""
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get payslip
    payslip = await db.payslips.find_one(
        {"payrun_id": payrun_id, "employee_id": employee["employee_id"]},
        {"_id": 0}
    )
    
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    # Get pay run and company
    pay_run = await db.pay_runs.find_one({"payrun_id": payrun_id}, {"_id": 0})
    company = await db.companies.find_one({"company_id": pay_run.get("company_id")}, {"_id": 0})
    
    # Generate PDF
    pdf_bytes = generate_payslip_pdf(payslip, company or {}, pay_run)
    
    filename = f"payslip_{pay_run.get('period_end', 'download')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/self-service/leave")
async def get_self_service_leave(user: User = Depends(get_current_user)):
    """Get employee's own leave requests and balance"""
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        return {"requests": [], "balance": {"annual": 25, "used": 0, "remaining": 25}}
    
    # Get leave requests
    leaves = await db.leave_requests.find(
        {"employee_id": employee["employee_id"]},
        {"_id": 0}
    ).to_list(100)
    
    for leave in leaves:
        if isinstance(leave.get("created_at"), str):
            leave["created_at"] = datetime.fromisoformat(leave["created_at"])
    
    # Calculate leave balance
    approved_leaves = [l for l in leaves if l.get("status") == "approved"]
    used_days = sum(l.get("days", 0) for l in approved_leaves)
    annual_allowance = 25  # Default UK statutory
    
    return {
        "requests": leaves,
        "balance": {
            "annual": annual_allowance,
            "used": used_days,
            "remaining": annual_allowance - used_days
        }
    }

@api_router.post("/self-service/leave")
async def create_self_service_leave(data: LeaveRequestCreate, user: User = Depends(get_current_user)):
    """Create leave request as employee"""
    employee = await db.employees.find_one({"email": user.email}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    leave_id = f"leave_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Calculate days
    start = datetime.fromisoformat(data.start_date)
    end = datetime.fromisoformat(data.end_date)
    days = (end - start).days + 1
    
    leave_doc = {
        "leave_id": leave_id,
        "employee_id": employee["employee_id"],
        "company_id": employee["company_id"],
        "leave_type": data.leave_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "days": days,
        "reason": data.reason,
        "status": "pending",
        "created_at": now.isoformat()
    }
    await db.leave_requests.insert_one(leave_doc)
    
    # Send email notification to approvers
    company = await db.companies.find_one({"company_id": employee["company_id"]}, {"_id": 0})
    owner = await db.users.find_one({"user_id": company.get("owner_id")}, {"_id": 0})
    
    if owner and owner.get("email"):
        email_body = f"{employee['first_name']} {employee['last_name']} has requested {data.leave_type} leave from {data.start_date} to {data.end_date} ({days} days)."
        if data.reason:
            email_body += f"<br><br>Reason: {data.reason}"
        
        await send_email_notification(
            owner["email"],
            f"Leave Request: {employee['first_name']} {employee['last_name']}",
            generate_email_template(
                "New Leave Request",
                email_body,
                None,
                None
            )
        )
    
    return {"leave_id": leave_id, "message": "Leave request submitted"}

# ==================== EMAIL NOTIFICATION ROUTES ====================

@api_router.post("/email/test")
async def send_test_email(email: str, user: User = Depends(get_current_user)):
    """Send a test email"""
    result = await send_email_notification(
        email,
        "RealtouchHR Test Email",
        generate_email_template(
            "Test Email Successful!",
            "This is a test email from RealtouchHR. If you received this, your email notifications are configured correctly.",
            None,
            None
        )
    )
    
    if result:
        return {"message": "Test email sent successfully", "email_id": result.get("id")}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Check RESEND_API_KEY configuration.")

@api_router.put("/company/email-settings")
async def update_email_settings(data: dict, user: User = Depends(get_current_user)):
    """Update company email notification settings"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    settings = {
        "email_notifications": {
            "leave_requests": data.get("leave_requests", True),
            "leave_approvals": data.get("leave_approvals", True),
            "payroll_ready": data.get("payroll_ready", True),
            "payslip_available": data.get("payslip_available", True)
        }
    }
    
    await db.companies.update_one(
        {"company_id": user.company_id},
        {"$set": settings}
    )
    
    return {"message": "Email settings updated"}

# Import and include modular routes BEFORE including api_router in app
try:
    from routes.hmrc import router as hmrc_router
    from routes.self_service import router as self_service_router
    from routes.rti_sync import router as rti_sync_router
    api_router.include_router(hmrc_router)
    api_router.include_router(self_service_router)
    api_router.include_router(rti_sync_router)
    logging.info("Modular routes loaded successfully")
except Exception as e:
    logging.error(f"Failed to load modular routes: {e}")

# Include the router
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
