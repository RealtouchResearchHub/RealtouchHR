"""
RealtouchHR - Right to Work (RTW) Service
UK Right to Work Check Management and Compliance

Every UK employer must conduct a Right to Work check before an employee's first day.
Sponsoring employers must conduct follow-up checks when time-limited RTW expires.

Features:
- Record RTW checks with document verification
- Track RTW status and expiry dates
- Automated follow-up date calculation (28 days before expiry)
- RTW status computation (valid, expiring_soon, expired, not_checked)
- Dashboard statistics
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

class RTWCheckType(str, Enum):
    """Types of Right to Work checks"""
    MANUAL = "manual"  # Manual document check
    IDVT = "idvt"  # Identity Document Validation Technology
    HOME_OFFICE_ONLINE = "home_office_online"  # Home Office online service
    SHARE_CODE = "share_code"  # Using Home Office share code


class RTWDocumentType(str, Enum):
    """Document types for RTW verification"""
    # List A - Permanent right to work
    BRITISH_PASSPORT = "british_passport"
    IRISH_PASSPORT = "irish_passport"
    UK_BIRTH_CERTIFICATE_WITH_NI = "uk_birth_certificate_with_ni"
    CERTIFICATE_OF_ENTITLEMENT = "certificate_of_entitlement"
    CERTIFICATE_OF_NATURALISATION = "certificate_of_naturalisation"
    CERTIFICATE_OF_REGISTRATION = "certificate_of_registration"
    
    # List B - Time-limited right to work
    BRP = "brp"  # Biometric Residence Permit
    BRC = "brc"  # Biometric Residence Card
    FRONTIER_WORKER_PERMIT = "frontier_worker_permit"
    IMMIGRATION_STATUS_DOCUMENT = "immigration_status_document"
    EVISA = "evisa"  # Electronic visa/status
    EU_SETTLEMENT_SCHEME = "eu_settlement_scheme"
    POSITIVE_VERIFICATION_LETTER = "positive_verification_letter"
    APPLICATION_REGISTRATION_CARD = "application_registration_card"
    
    OTHER = "other"


class RTWStatus(str, Enum):
    """Right to Work status"""
    NOT_CHECKED = "not_checked"  # No RTW check recorded
    VALID = "valid"  # Check valid, not expiring soon
    EXPIRING_SOON = "expiring_soon"  # Expiry within 60 days
    EXPIRED = "expired"  # RTW has expired
    PERMANENT = "permanent"  # Permanent right to work (no expiry)


# Document types by check type
DOCUMENT_TYPES_BY_CHECK = {
    RTWCheckType.MANUAL.value: [
        RTWDocumentType.BRITISH_PASSPORT,
        RTWDocumentType.IRISH_PASSPORT,
        RTWDocumentType.UK_BIRTH_CERTIFICATE_WITH_NI,
        RTWDocumentType.CERTIFICATE_OF_ENTITLEMENT,
        RTWDocumentType.CERTIFICATE_OF_NATURALISATION,
        RTWDocumentType.CERTIFICATE_OF_REGISTRATION,
        RTWDocumentType.BRP,
        RTWDocumentType.BRC,
        RTWDocumentType.FRONTIER_WORKER_PERMIT,
        RTWDocumentType.IMMIGRATION_STATUS_DOCUMENT,
        RTWDocumentType.OTHER
    ],
    RTWCheckType.IDVT.value: [
        RTWDocumentType.BRITISH_PASSPORT,
        RTWDocumentType.IRISH_PASSPORT
    ],
    RTWCheckType.HOME_OFFICE_ONLINE.value: [
        RTWDocumentType.EVISA,
        RTWDocumentType.EU_SETTLEMENT_SCHEME,
        RTWDocumentType.BRP,
        RTWDocumentType.OTHER
    ],
    RTWCheckType.SHARE_CODE.value: [
        RTWDocumentType.EVISA,
        RTWDocumentType.EU_SETTLEMENT_SCHEME,
        RTWDocumentType.OTHER
    ]
}

# Documents that indicate permanent right to work
PERMANENT_RTW_DOCUMENTS = [
    RTWDocumentType.BRITISH_PASSPORT.value,
    RTWDocumentType.IRISH_PASSPORT.value,
    RTWDocumentType.UK_BIRTH_CERTIFICATE_WITH_NI.value,
    RTWDocumentType.CERTIFICATE_OF_ENTITLEMENT.value,
    RTWDocumentType.CERTIFICATE_OF_NATURALISATION.value,
    RTWDocumentType.CERTIFICATE_OF_REGISTRATION.value
]


# ==================== DATA CLASSES ====================

@dataclass
class RTWCheck:
    """A Right to Work check record"""
    check_id: str
    employee_id: str
    company_id: str
    check_date: date
    check_type: RTWCheckType
    document_type: RTWDocumentType
    document_number: Optional[str] = None
    document_expiry_date: Optional[date] = None
    follow_up_date: Optional[date] = None  # 28 days before expiry
    conducted_by: str = None  # User ID who conducted the check
    conducted_by_name: Optional[str] = None
    status: RTWStatus = RTWStatus.VALID
    share_code: Optional[str] = None  # For share code checks
    online_check_reference: Optional[str] = None  # Reference from Home Office
    document_copy_url: Optional[str] = None  # URL to uploaded document
    notes: Optional[str] = None
    confirmation_signed: bool = False  # "I confirm I have seen the original..."
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "check_date": self.check_date.isoformat() if self.check_date else None,
            "check_type": self.check_type.value if isinstance(self.check_type, RTWCheckType) else self.check_type,
            "document_type": self.document_type.value if isinstance(self.document_type, RTWDocumentType) else self.document_type,
            "document_number": self.document_number,
            "document_expiry_date": self.document_expiry_date.isoformat() if self.document_expiry_date else None,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "conducted_by": self.conducted_by,
            "conducted_by_name": self.conducted_by_name,
            "status": self.status.value if isinstance(self.status, RTWStatus) else self.status,
            "share_code": self.share_code,
            "online_check_reference": self.online_check_reference,
            "document_copy_url": self.document_copy_url,
            "notes": self.notes,
            "confirmation_signed": self.confirmation_signed,
            "created_at": self.created_at.isoformat()
        }


# ==================== RTW SERVICE ====================

class RTWService:
    """Service for Right to Work check management"""
    
    def __init__(self):
        self.expiry_warning_days = 60  # Warn when expiring within 60 days
        self.follow_up_days_before = 28  # Follow-up date is 28 days before expiry
    
    async def record_rtw_check(
        self,
        employee_id: str,
        company_id: str,
        check_date: date,
        check_type: str,
        document_type: str,
        conducted_by: str,
        document_number: Optional[str] = None,
        document_expiry_date: Optional[date] = None,
        share_code: Optional[str] = None,
        online_check_reference: Optional[str] = None,
        document_copy_url: Optional[str] = None,
        notes: Optional[str] = None,
        confirmation_signed: bool = False
    ) -> RTWCheck:
        """Record a new RTW check"""
        # Validate employee exists
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        )
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # Get conductor name
        conductor = await db.users.find_one(
            {"user_id": conducted_by},
            {"name": 1, "_id": 0}
        )
        conducted_by_name = conductor.get("name") if conductor else None
        
        # Calculate follow-up date (28 days before expiry)
        follow_up_date = None
        if document_expiry_date:
            follow_up_date = document_expiry_date - timedelta(days=self.follow_up_days_before)
        
        # Determine initial status
        status = self._calculate_rtw_status(document_type, document_expiry_date)
        
        check = RTWCheck(
            check_id=f"rtw_{uuid.uuid4().hex[:12]}",
            employee_id=employee_id,
            company_id=company_id,
            check_date=check_date,
            check_type=RTWCheckType(check_type),
            document_type=RTWDocumentType(document_type),
            document_number=document_number,
            document_expiry_date=document_expiry_date,
            follow_up_date=follow_up_date,
            conducted_by=conducted_by,
            conducted_by_name=conducted_by_name,
            status=status,
            share_code=share_code,
            online_check_reference=online_check_reference,
            document_copy_url=document_copy_url,
            notes=notes,
            confirmation_signed=confirmation_signed
        )
        
        await db.rtw_checks.insert_one(check.to_dict())
        
        # Update employee RTW status
        await self._update_employee_rtw_status(employee_id)
        
        return check
    
    def _calculate_rtw_status(
        self,
        document_type: str,
        document_expiry_date: Optional[date]
    ) -> RTWStatus:
        """Calculate RTW status based on document type and expiry"""
        # Check if permanent RTW document
        if document_type in PERMANENT_RTW_DOCUMENTS:
            return RTWStatus.PERMANENT
        
        if not document_expiry_date:
            return RTWStatus.VALID
        
        today = date.today()
        days_until_expiry = (document_expiry_date - today).days
        
        if days_until_expiry < 0:
            return RTWStatus.EXPIRED
        elif days_until_expiry <= self.expiry_warning_days:
            return RTWStatus.EXPIRING_SOON
        else:
            return RTWStatus.VALID
    
    async def _update_employee_rtw_status(self, employee_id: str):
        """Update employee's RTW status based on latest check"""
        latest_check = await db.rtw_checks.find_one(
            {"employee_id": employee_id},
            {"_id": 0},
            sort=[("check_date", -1)]
        )
        
        if latest_check:
            # Recalculate status in case it changed
            doc_type = latest_check.get("document_type")
            expiry = latest_check.get("document_expiry_date")
            
            if expiry:
                expiry_date = date.fromisoformat(expiry)
            else:
                expiry_date = None
            
            status = self._calculate_rtw_status(doc_type, expiry_date)
            
            await db.employees.update_one(
                {"employee_id": employee_id},
                {"$set": {
                    "rtw_status": status.value,
                    "rtw_last_check_date": latest_check.get("check_date"),
                    "rtw_expiry_date": expiry,
                    "rtw_follow_up_date": latest_check.get("follow_up_date"),
                    "rtw_document_type": doc_type
                }}
            )
        else:
            await db.employees.update_one(
                {"employee_id": employee_id},
                {"$set": {"rtw_status": RTWStatus.NOT_CHECKED.value}}
            )
    
    async def get_employee_rtw_checks(
        self,
        employee_id: str,
        company_id: str
    ) -> List[dict]:
        """Get all RTW checks for an employee"""
        checks = await db.rtw_checks.find(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0}
        ).sort("check_date", -1).to_list(100)
        
        return checks
    
    async def get_employee_rtw_status(
        self,
        employee_id: str,
        company_id: str
    ) -> dict:
        """Get current RTW status for an employee"""
        employee = await db.employees.find_one(
            {"employee_id": employee_id, "company_id": company_id},
            {"_id": 0, "rtw_status": 1, "rtw_last_check_date": 1, 
             "rtw_expiry_date": 1, "rtw_follow_up_date": 1, "first_name": 1, "last_name": 1}
        )
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        rtw_status = employee.get("rtw_status", RTWStatus.NOT_CHECKED.value)
        
        # Get latest check
        latest_check = await db.rtw_checks.find_one(
            {"employee_id": employee_id},
            {"_id": 0},
            sort=[("check_date", -1)]
        )
        
        return {
            "employee_id": employee_id,
            "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
            "status": rtw_status,
            "last_check_date": employee.get("rtw_last_check_date"),
            "expiry_date": employee.get("rtw_expiry_date"),
            "follow_up_date": employee.get("rtw_follow_up_date"),
            "latest_check": latest_check
        }
    
    async def get_rtw_summary(self, company_id: str) -> dict:
        """Get RTW status summary across all employees"""
        employees = await db.employees.find(
            {"company_id": company_id, "status": "active"},
            {"_id": 0, "rtw_status": 1}
        ).to_list(10000)
        
        summary = {
            "total_employees": len(employees),
            "valid": 0,
            "permanent": 0,
            "expiring_soon": 0,
            "expired": 0,
            "not_checked": 0
        }
        
        for emp in employees:
            status = emp.get("rtw_status", RTWStatus.NOT_CHECKED.value)
            if status == RTWStatus.VALID.value:
                summary["valid"] += 1
            elif status == RTWStatus.PERMANENT.value:
                summary["permanent"] += 1
            elif status == RTWStatus.EXPIRING_SOON.value:
                summary["expiring_soon"] += 1
            elif status == RTWStatus.EXPIRED.value:
                summary["expired"] += 1
            else:
                summary["not_checked"] += 1
        
        return summary
    
    async def get_expiring_rtw(
        self,
        company_id: str,
        days: int = 60
    ) -> List[dict]:
        """Get employees with RTW expiring within N days"""
        cutoff_date = (date.today() + timedelta(days=days)).isoformat()
        
        employees = await db.employees.find(
            {
                "company_id": company_id,
                "status": "active",
                "rtw_expiry_date": {"$lte": cutoff_date, "$gte": date.today().isoformat()}
            },
            {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1,
             "rtw_expiry_date": 1, "rtw_follow_up_date": 1, "rtw_status": 1}
        ).sort("rtw_expiry_date", 1).to_list(1000)
        
        return employees
    
    async def bulk_status_update(self, company_id: str) -> dict:
        """Re-evaluate RTW status for all employees"""
        employees = await db.employees.find(
            {"company_id": company_id},
            {"employee_id": 1, "_id": 0}
        ).to_list(10000)
        
        updated = 0
        for emp in employees:
            await self._update_employee_rtw_status(emp["employee_id"])
            updated += 1
        
        return {"status": "completed", "employees_updated": updated}
    
    def get_document_types_for_check_type(self, check_type: str) -> List[dict]:
        """Get valid document types for a check type"""
        doc_types = DOCUMENT_TYPES_BY_CHECK.get(check_type, [])
        return [
            {"code": dt.value, "name": dt.value.replace("_", " ").title()}
            for dt in doc_types
        ]


# Singleton instance
rtw_service = RTWService()
