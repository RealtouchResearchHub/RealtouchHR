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

# Create the main app
app = FastAPI(title="RealtouchHR API", version="1.0.0")

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
    
    update_fields = {k: v for k, v in data.items() if k in ["name", "industry", "size", "address", "payroll_frequency", "setup_completed"]}
    
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
    
    update_fields = {}
    if "status" in data:
        update_fields["status"] = data["status"]
        if data["status"] == "approved":
            update_fields["approved_by"] = user.user_id
    
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
    
    # Use OpenAI for response (with Emergent key)
    try:
        from openai import OpenAI
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return CopilotResponse(
                response="AI Copilot is currently unavailable. Please ensure the API key is configured.",
                suggestions=["Check system configuration", "Contact administrator"],
                requires_approval=False
            )
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data.message}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
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
