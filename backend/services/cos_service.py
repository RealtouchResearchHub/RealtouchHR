"""
RealtouchHR - Certificate of Sponsorship (CoS) Service
CoS Register Management for UKVI Sponsor Licence Compliance

Sponsors must maintain a register of every CoS they have been allocated and assigned.
This service provides CoS management with tracking and compliance alerts.
"""

import os
import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid

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


# ==================== ENUMS ====================

class CoSType(str, Enum):
    """Certificate of Sponsorship types"""
    DEFINED = "defined"  # For extension/change of employer
    UNDEFINED = "undefined"  # For new visa application


class CoSStatus(str, Enum):
    """CoS status"""
    UNASSIGNED = "unassigned"  # Allocated but not assigned to employee
    ASSIGNED = "assigned"  # Assigned to employee, visa application pending
    USED = "used"  # Visa granted and employee working
    EXPIRED = "expired"  # CoS expired before use
    WITHDRAWN = "withdrawn"  # Withdrawn by sponsor
    CANCELLED = "cancelled"  # Cancelled by Home Office


# SOC codes with going rates (sample data - should be loaded from external source)
SOC_GOING_RATES = {
    "2133": {"title": "IT business analysts, architects and systems designers", "annual": 52000, "hourly": 26.92},
    "2134": {"title": "Programmers and software development professionals", "annual": 46900, "hourly": 24.28},
    "2135": {"title": "IT project and programme managers", "annual": 52000, "hourly": 26.92},
    "2136": {"title": "IT and telecommunications professionals n.e.c.", "annual": 37300, "hourly": 19.32},
    "2139": {"title": "IT specialist managers", "annual": 62200, "hourly": 32.21},
    "2211": {"title": "Medical practitioners", "annual": 43800, "hourly": 22.68},
    "2212": {"title": "Psychologists", "annual": 43000, "hourly": 22.26},
    "2231": {"title": "Nurses", "annual": 28000, "hourly": 14.50},
    "2421": {"title": "Chartered and certified accountants", "annual": 46000, "hourly": 23.82},
    "2423": {"title": "Management consultants and business analysts", "annual": 42600, "hourly": 22.05},
    "3131": {"title": "IT operations technicians", "annual": 28800, "hourly": 14.91},
    "3132": {"title": "IT user support technicians", "annual": 26200, "hourly": 13.56},
}


# ==================== DATA CLASSES ====================

@dataclass
class CertificateOfSponsorship:
    """A Certificate of Sponsorship record"""
    cos_id: str
    company_id: str
    cos_reference_number: str  # Assigned by Home Office SMS
    cos_type: CoSType
    status: CoSStatus
    employee_id: Optional[str] = None  # Nullable for unassigned CoS
    employee_name: Optional[str] = None
    job_title: str = ""
    soc_code: str = ""
    soc_title: Optional[str] = None
    salary_offered: float = 0
    hours_per_week: float = 37.5
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    assigned_date: Optional[date] = None
    notes: Optional[str] = None
    created_by: str = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "cos_id": self.cos_id,
            "company_id": self.company_id,
            "cos_reference_number": self.cos_reference_number,
            "cos_type": self.cos_type.value if isinstance(self.cos_type, CoSType) else self.cos_type,
            "status": self.status.value if isinstance(self.status, CoSStatus) else self.status,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "job_title": self.job_title,
            "soc_code": self.soc_code,
            "soc_title": self.soc_title,
            "salary_offered": self.salary_offered,
            "hours_per_week": self.hours_per_week,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "assigned_date": self.assigned_date.isoformat() if self.assigned_date else None,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== COS SERVICE ====================

class CoSService:
    """Service for Certificate of Sponsorship management"""
    
    def __init__(self):
        self.general_threshold = 38700  # General salary threshold
        self.new_entrant_threshold = 30960  # New entrant rate
    
    async def create_cos(
        self,
        company_id: str,
        cos_reference_number: str,
        cos_type: str,
        job_title: str,
        soc_code: str,
        salary_offered: float,
        hours_per_week: float = 37.5,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: str = None
    ) -> CertificateOfSponsorship:
        """Create a new CoS record"""
        # Check for duplicate reference number
        existing = await db.certificates_of_sponsorship.find_one(
            {"cos_reference_number": cos_reference_number}
        )
        if existing:
            raise ValueError(f"CoS reference {cos_reference_number} already exists")
        
        # Get SOC title
        soc_info = SOC_GOING_RATES.get(soc_code, {})
        soc_title = soc_info.get("title", "Unknown occupation")
        
        # Determine initial status
        status = CoSStatus.UNASSIGNED if not employee_id else CoSStatus.ASSIGNED
        assigned_date = date.today() if employee_id else None
        
        # Get employee name if assigned
        employee_name = None
        if employee_id:
            emp = await db.employees.find_one(
                {"employee_id": employee_id},
                {"first_name": 1, "last_name": 1, "_id": 0}
            )
            if emp:
                employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        
        cos = CertificateOfSponsorship(
            cos_id=f"cos_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            cos_reference_number=cos_reference_number,
            cos_type=CoSType(cos_type),
            status=status,
            employee_id=employee_id,
            employee_name=employee_name,
            job_title=job_title,
            soc_code=soc_code,
            soc_title=soc_title,
            salary_offered=salary_offered,
            hours_per_week=hours_per_week,
            start_date=start_date,
            end_date=end_date,
            assigned_date=assigned_date,
            notes=notes,
            created_by=created_by
        )
        
        await db.certificates_of_sponsorship.insert_one(cos.to_dict())
        
        # Update employee if assigned
        if employee_id:
            await db.employees.update_one(
                {"employee_id": employee_id},
                {"$set": {
                    "cos_reference": cos_reference_number,
                    "cos_id": cos.cos_id
                }}
            )
        
        return cos
    
    async def assign_cos(
        self,
        cos_id: str,
        employee_id: str,
        company_id: str
    ) -> dict:
        """Assign a CoS to an employee"""
        # Verify CoS exists and is unassigned
        cos = await db.certificates_of_sponsorship.find_one(
            {"cos_id": cos_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not cos:
            raise ValueError(f"CoS {cos_id} not found")
        
        if cos.get("status") != CoSStatus.UNASSIGNED.value:
            raise ValueError(f"CoS is already assigned or not available")
        
        # Get employee
        emp = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"first_name": 1, "last_name": 1, "_id": 0}
        )
        
        if not emp:
            raise ValueError(f"Employee {employee_id} not found")
        
        employee_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        now = datetime.now(timezone.utc)
        
        await db.certificates_of_sponsorship.update_one(
            {"cos_id": cos_id},
            {"$set": {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "status": CoSStatus.ASSIGNED.value,
                "assigned_date": date.today().isoformat(),
                "updated_at": now.isoformat()
            }}
        )
        
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "cos_reference": cos["cos_reference_number"],
                "cos_id": cos_id
            }}
        )
        
        return {"status": "assigned", "cos_id": cos_id, "employee_id": employee_id}
    
    async def update_cos_status(
        self,
        cos_id: str,
        company_id: str,
        new_status: str
    ) -> dict:
        """Update CoS status"""
        now = datetime.now(timezone.utc)
        
        result = await db.certificates_of_sponsorship.update_one(
            {"cos_id": cos_id, "company_id": company_id},
            {"$set": {
                "status": new_status,
                "updated_at": now.isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"CoS {cos_id} not found")
        
        return {"status": new_status, "cos_id": cos_id}
    
    async def get_all_cos(
        self,
        company_id: str,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get all CoS records for a company"""
        query = {"company_id": company_id}
        if status:
            query["status"] = status
        
        records = await db.certificates_of_sponsorship.find(
            query, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
        
        # Calculate days remaining for each
        today = date.today()
        for record in records:
            end_date = record.get("end_date")
            if end_date:
                end = date.fromisoformat(end_date)
                record["days_remaining"] = (end - today).days
            else:
                record["days_remaining"] = None
        
        return records
    
    async def get_cos(self, cos_id: str, company_id: str) -> dict:
        """Get a single CoS record"""
        cos = await db.certificates_of_sponsorship.find_one(
            {"cos_id": cos_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not cos:
            raise ValueError(f"CoS {cos_id} not found")
        
        return cos
    
    async def get_expiring_cos(
        self,
        company_id: str,
        days: int = 60
    ) -> List[dict]:
        """Get CoS expiring within N days"""
        cutoff_date = (date.today() + timedelta(days=days)).isoformat()
        
        records = await db.certificates_of_sponsorship.find(
            {
                "company_id": company_id,
                "status": {"$in": [CoSStatus.ASSIGNED.value, CoSStatus.USED.value]},
                "end_date": {"$lte": cutoff_date, "$gte": date.today().isoformat()}
            },
            {"_id": 0}
        ).sort("end_date", 1).to_list(1000)
        
        return records
    
    async def delete_cos(self, cos_id: str, company_id: str) -> dict:
        """Soft delete (cancel) a CoS"""
        now = datetime.now(timezone.utc)
        
        cos = await db.certificates_of_sponsorship.find_one(
            {"cos_id": cos_id, "company_id": company_id},
            {"employee_id": 1, "_id": 0}
        )
        
        if not cos:
            raise ValueError(f"CoS {cos_id} not found")
        
        await db.certificates_of_sponsorship.update_one(
            {"cos_id": cos_id},
            {"$set": {
                "status": CoSStatus.CANCELLED.value,
                "updated_at": now.isoformat()
            }}
        )
        
        # Remove from employee if assigned
        if cos.get("employee_id"):
            await db.employees.update_one(
                {"employee_id": cos["employee_id"]},
                {"$unset": {"cos_reference": "", "cos_id": ""}}
            )
        
        return {"status": "cancelled", "cos_id": cos_id}
    
    # ==================== SOC CODES ====================
    
    def search_soc_codes(self, query: str) -> List[dict]:
        """Search SOC codes by code or title"""
        results = []
        query_lower = query.lower()
        
        for code, info in SOC_GOING_RATES.items():
            if query_lower in code or query_lower in info["title"].lower():
                results.append({
                    "soc_code": code,
                    "title": info["title"],
                    "going_rate_annual": info["annual"],
                    "going_rate_hourly": info["hourly"]
                })
        
        return results
    
    def get_soc_going_rate(self, soc_code: str) -> dict:
        """Get going rate for a SOC code"""
        info = SOC_GOING_RATES.get(soc_code)
        
        if not info:
            return {"error": "SOC code not found"}
        
        return {
            "soc_code": soc_code,
            "title": info["title"],
            "going_rate_annual": info["annual"],
            "going_rate_hourly": info["hourly"],
            "general_threshold": self.general_threshold,
            "new_entrant_threshold": self.new_entrant_threshold
        }
    
    # ==================== SALARY THRESHOLD CHECKS ====================
    
    async def check_salary_thresholds(self, company_id: str) -> List[dict]:
        """Check all sponsored workers against salary thresholds"""
        issues = []
        
        # Get all active CoS
        cos_records = await db.certificates_of_sponsorship.find(
            {
                "company_id": company_id,
                "status": {"$in": [CoSStatus.ASSIGNED.value, CoSStatus.USED.value]}
            },
            {"_id": 0}
        ).to_list(1000)
        
        for cos in cos_records:
            soc_code = cos.get("soc_code")
            salary = cos.get("salary_offered", 0)
            hours = cos.get("hours_per_week", 37.5)
            
            # Get going rate
            going_rate_info = SOC_GOING_RATES.get(soc_code, {})
            going_rate = going_rate_info.get("annual", 0)
            
            # Pro-rate for part-time
            if hours < 37.5 and hours > 0:
                pro_rated_going_rate = going_rate * (hours / 37.5)
            else:
                pro_rated_going_rate = going_rate
            
            issue = None
            
            # Check against general threshold
            if salary < self.general_threshold:
                issue = {
                    "cos_id": cos["cos_id"],
                    "employee_id": cos.get("employee_id"),
                    "employee_name": cos.get("employee_name"),
                    "issue_type": "below_general_threshold",
                    "current_salary": salary,
                    "required_minimum": self.general_threshold,
                    "shortfall": self.general_threshold - salary
                }
            
            # Check against going rate
            if salary < pro_rated_going_rate:
                issue = {
                    "cos_id": cos["cos_id"],
                    "employee_id": cos.get("employee_id"),
                    "employee_name": cos.get("employee_name"),
                    "issue_type": "below_going_rate",
                    "current_salary": salary,
                    "required_minimum": pro_rated_going_rate,
                    "shortfall": pro_rated_going_rate - salary,
                    "soc_code": soc_code
                }
            
            if issue:
                issues.append(issue)
        
        return issues


# Singleton instance
cos_service = CoSService()
