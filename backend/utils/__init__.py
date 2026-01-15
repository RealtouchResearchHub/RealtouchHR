"""
RealtouchHR - Utility Functions
Common helpers and utilities
"""
import os
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# ==================== DATABASE ====================

mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# ==================== JWT CONFIG ====================

JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

# ==================== PASSWORD UTILS ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ==================== JWT UTILS ====================

def create_jwt_token(user_id: str, email: str, role: str = "owner") -> str:
    """Create a JWT token for authentication"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode a JWT token"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ==================== ID GENERATORS ====================

def generate_id(prefix: str) -> str:
    """Generate a unique ID with a prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_user_id() -> str:
    return generate_id("user")


def generate_company_id() -> str:
    return generate_id("company")


def generate_employee_id() -> str:
    return generate_id("emp")


def generate_payrun_id() -> str:
    return generate_id("payrun")


def generate_leave_id() -> str:
    return generate_id("leave")


def generate_document_id() -> str:
    return generate_id("doc")


def generate_shift_id() -> str:
    return generate_id("shift")


def generate_timesheet_id() -> str:
    return generate_id("ts")


def generate_audit_id() -> str:
    return generate_id("audit")


def generate_task_id() -> str:
    return generate_id("task")


def generate_notification_id() -> str:
    return generate_id("notif")


def generate_submission_id() -> str:
    return generate_id("rti")


def generate_role_id() -> str:
    return generate_id("role")


# ==================== DATE UTILS ====================

def now_utc() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def now_iso() -> str:
    """Get current UTC datetime as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(dt_str: str) -> datetime:
    """Parse an ISO datetime string"""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def days_between(start_date: str, end_date: str) -> int:
    """Calculate days between two date strings (YYYY-MM-DD)"""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return (end - start).days + 1


# ==================== COMPLIANCE UTILS ====================

def calculate_compliance_score(employee: dict) -> tuple:
    """Calculate compliance score and issues for an employee"""
    issues = []
    required_fields = ["ni_number", "tax_code", "bank_account", "bank_sort_code", "salary"]
    
    for field in required_fields:
        if not employee.get(field):
            issues.append(f"Missing {field.replace('_', ' ')}")
    
    # Validate NI number format (UK format: AB123456C)
    ni = employee.get("ni_number", "")
    if ni and not is_valid_ni_number(ni):
        issues.append("Invalid NI number format")
    
    # Validate tax code format
    tax_code = employee.get("tax_code", "")
    if tax_code and not is_valid_tax_code(tax_code):
        issues.append("Invalid tax code format")
    
    score = max(0, 100 - (len(issues) * 20))
    return score, issues


def is_valid_ni_number(ni: str) -> bool:
    """Validate UK National Insurance number format"""
    import re
    # Format: 2 letters, 6 digits, 1 letter (A/B/C/D)
    pattern = r'^[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$'
    return bool(re.match(pattern, ni.upper().replace(' ', '')))


def is_valid_tax_code(tax_code: str) -> bool:
    """Validate UK tax code format"""
    import re
    # Common formats: 1257L, BR, D0, NT, etc.
    pattern = r'^(\d{1,4}[LMNPTY]|BR|D[01]|NT|0T|K\d+|S\d{1,4}[LMNPTY]|C\d{1,4}[LMNPTY])$'
    return bool(re.match(pattern, tax_code.upper().replace(' ', '')))


# ==================== UK TAX CALCULATIONS ====================

# 2024/25 UK Tax Rates
UK_TAX_CONFIG = {
    "personal_allowance": 12570,
    "basic_rate_threshold": 50270,
    "higher_rate_threshold": 125140,
    "basic_rate": 0.20,
    "higher_rate": 0.40,
    "additional_rate": 0.45,
    # National Insurance
    "ni_primary_threshold": 12570,  # Annual
    "ni_upper_earnings_limit": 50270,
    "ni_rate_below_uel": 0.12,
    "ni_rate_above_uel": 0.02,
    # Employer NI
    "ni_employer_threshold": 9100,
    "ni_employer_rate": 0.138,
}


def calculate_monthly_tax(annual_salary: float, tax_code: str = "1257L") -> float:
    """Calculate monthly PAYE tax based on annual salary and tax code"""
    # Parse tax code to get personal allowance
    personal_allowance = UK_TAX_CONFIG["personal_allowance"]
    if tax_code and tax_code[:-1].isdigit():
        personal_allowance = int(tax_code[:-1]) * 10
    
    taxable_income = max(0, annual_salary - personal_allowance)
    
    # Calculate annual tax
    annual_tax = 0
    remaining = taxable_income
    
    # Basic rate band
    basic_band = UK_TAX_CONFIG["basic_rate_threshold"] - personal_allowance
    if remaining > 0:
        basic_taxable = min(remaining, basic_band)
        annual_tax += basic_taxable * UK_TAX_CONFIG["basic_rate"]
        remaining -= basic_taxable
    
    # Higher rate band
    higher_band = UK_TAX_CONFIG["higher_rate_threshold"] - UK_TAX_CONFIG["basic_rate_threshold"]
    if remaining > 0:
        higher_taxable = min(remaining, higher_band)
        annual_tax += higher_taxable * UK_TAX_CONFIG["higher_rate"]
        remaining -= higher_taxable
    
    # Additional rate
    if remaining > 0:
        annual_tax += remaining * UK_TAX_CONFIG["additional_rate"]
    
    return round(annual_tax / 12, 2)


def calculate_monthly_ni(annual_salary: float) -> float:
    """Calculate monthly employee National Insurance contributions"""
    monthly_salary = annual_salary / 12
    monthly_primary_threshold = UK_TAX_CONFIG["ni_primary_threshold"] / 12
    monthly_uel = UK_TAX_CONFIG["ni_upper_earnings_limit"] / 12
    
    if monthly_salary <= monthly_primary_threshold:
        return 0
    
    ni = 0
    
    # Below UEL
    if monthly_salary <= monthly_uel:
        ni = (monthly_salary - monthly_primary_threshold) * UK_TAX_CONFIG["ni_rate_below_uel"]
    else:
        # Below UEL portion
        ni = (monthly_uel - monthly_primary_threshold) * UK_TAX_CONFIG["ni_rate_below_uel"]
        # Above UEL portion
        ni += (monthly_salary - monthly_uel) * UK_TAX_CONFIG["ni_rate_above_uel"]
    
    return round(ni, 2)


def calculate_employer_ni(annual_salary: float) -> float:
    """Calculate monthly employer National Insurance contributions"""
    monthly_salary = annual_salary / 12
    monthly_threshold = UK_TAX_CONFIG["ni_employer_threshold"] / 12
    
    if monthly_salary <= monthly_threshold:
        return 0
    
    ni = (monthly_salary - monthly_threshold) * UK_TAX_CONFIG["ni_employer_rate"]
    return round(ni, 2)


# ==================== CURRENCY CONFIG ====================

SUPPORTED_CURRENCIES = {
    "GBP": {"symbol": "£", "name": "British Pound", "rate_to_gbp": 1.0},
    "USD": {"symbol": "$", "name": "US Dollar", "rate_to_gbp": 0.79},
    "EUR": {"symbol": "€", "name": "Euro", "rate_to_gbp": 0.85},
    "CAD": {"symbol": "C$", "name": "Canadian Dollar", "rate_to_gbp": 0.58},
    "AUD": {"symbol": "A$", "name": "Australian Dollar", "rate_to_gbp": 0.52},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "rate_to_gbp": 0.0053},
    "CHF": {"symbol": "Fr", "name": "Swiss Franc", "rate_to_gbp": 0.89},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "rate_to_gbp": 0.0094},
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount between currencies via GBP"""
    if from_currency == to_currency:
        return amount
    
    from_rate = SUPPORTED_CURRENCIES.get(from_currency, {}).get("rate_to_gbp", 1.0)
    to_rate = SUPPORTED_CURRENCIES.get(to_currency, {}).get("rate_to_gbp", 1.0)
    
    # Convert to GBP, then to target currency
    gbp_amount = amount * from_rate
    return round(gbp_amount / to_rate, 2)
