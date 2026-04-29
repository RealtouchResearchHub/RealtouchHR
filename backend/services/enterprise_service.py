"""
RealtouchHR - Enterprise Features Service
Multi-entity Payroll, Advanced RBAC, and SSO Support

Enterprise-grade features for larger organizations:
- Multi-entity/Multi-company payroll management
- Granular Role-Based Access Control (RBAC)
- SCIM provisioning support
- SAML SSO integration readiness
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import uuid
import hashlib

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


# ==================== RBAC DEFINITIONS ====================

class Permission(str, Enum):
    """Granular permissions for RBAC"""
    # Employee Management
    EMPLOYEE_VIEW = "employee:view"
    EMPLOYEE_CREATE = "employee:create"
    EMPLOYEE_EDIT = "employee:edit"
    EMPLOYEE_DELETE = "employee:delete"
    EMPLOYEE_IMPORT = "employee:import"
    
    # Payroll
    PAYROLL_VIEW = "payroll:view"
    PAYROLL_CREATE = "payroll:create"
    PAYROLL_APPROVE = "payroll:approve"
    PAYROLL_RUN = "payroll:run"
    PAYROLL_EXPORT = "payroll:export"
    
    # Leave Management
    LEAVE_VIEW = "leave:view"
    LEAVE_REQUEST = "leave:request"
    LEAVE_APPROVE = "leave:approve"
    LEAVE_SETTINGS = "leave:settings"
    
    # Time & Scheduling
    TIME_VIEW = "time:view"
    TIME_CLOCK = "time:clock"
    TIME_EDIT = "time:edit"
    TIME_APPROVE = "time:approve"
    SCHEDULE_VIEW = "schedule:view"
    SCHEDULE_EDIT = "schedule:edit"
    
    # Compliance
    COMPLIANCE_VIEW = "compliance:view"
    COMPLIANCE_MANAGE = "compliance:manage"
    RTI_SUBMIT = "rti:submit"
    UKVI_MANAGE = "ukvi:manage"
    
    # Documents
    DOCUMENTS_VIEW = "documents:view"
    DOCUMENTS_UPLOAD = "documents:upload"
    DOCUMENTS_DELETE = "documents:delete"
    ESIGN_REQUEST = "esign:request"
    
    # Reports & Analytics
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
    ANALYTICS_VIEW = "analytics:view"
    
    # Company Administration
    COMPANY_VIEW = "company:view"
    COMPANY_EDIT = "company:edit"
    COMPANY_SETTINGS = "company:settings"
    
    # User Management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    ROLE_MANAGE = "role:manage"
    
    # Multi-Entity
    ENTITY_VIEW = "entity:view"
    ENTITY_CREATE = "entity:create"
    ENTITY_MANAGE = "entity:manage"
    ENTITY_SWITCH = "entity:switch"
    
    # Audit
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"


# Predefined role templates
ROLE_TEMPLATES = {
    "owner": {
        "name": "Owner",
        "description": "Full system access - company owner",
        "permissions": [p.value for p in Permission],  # All permissions
        "is_system_role": True
    },
    "admin": {
        "name": "Administrator",
        "description": "Full administrative access",
        "permissions": [p.value for p in Permission if not p.value.startswith("entity:")],
        "is_system_role": True
    },
    "hr_manager": {
        "name": "HR Manager",
        "description": "Manage employees, leave, documents",
        "permissions": [
            Permission.EMPLOYEE_VIEW.value, Permission.EMPLOYEE_CREATE.value,
            Permission.EMPLOYEE_EDIT.value, Permission.EMPLOYEE_DELETE.value,
            Permission.EMPLOYEE_IMPORT.value,
            Permission.LEAVE_VIEW.value, Permission.LEAVE_APPROVE.value,
            Permission.LEAVE_SETTINGS.value,
            Permission.DOCUMENTS_VIEW.value, Permission.DOCUMENTS_UPLOAD.value,
            Permission.ESIGN_REQUEST.value,
            Permission.COMPLIANCE_VIEW.value, Permission.UKVI_MANAGE.value,
            Permission.REPORTS_VIEW.value, Permission.REPORTS_EXPORT.value,
            Permission.USER_VIEW.value
        ],
        "is_system_role": True
    },
    "payroll_admin": {
        "name": "Payroll Administrator",
        "description": "Manage payroll and RTI submissions",
        "permissions": [
            Permission.EMPLOYEE_VIEW.value,
            Permission.PAYROLL_VIEW.value, Permission.PAYROLL_CREATE.value,
            Permission.PAYROLL_APPROVE.value, Permission.PAYROLL_RUN.value,
            Permission.PAYROLL_EXPORT.value,
            Permission.COMPLIANCE_VIEW.value, Permission.RTI_SUBMIT.value,
            Permission.REPORTS_VIEW.value, Permission.REPORTS_EXPORT.value,
            Permission.AUDIT_VIEW.value
        ],
        "is_system_role": True
    },
    "manager": {
        "name": "Line Manager",
        "description": "Manage team members, approve leave/time",
        "permissions": [
            Permission.EMPLOYEE_VIEW.value,
            Permission.LEAVE_VIEW.value, Permission.LEAVE_APPROVE.value,
            Permission.TIME_VIEW.value, Permission.TIME_APPROVE.value,
            Permission.SCHEDULE_VIEW.value, Permission.SCHEDULE_EDIT.value,
            Permission.DOCUMENTS_VIEW.value,
            Permission.REPORTS_VIEW.value
        ],
        "is_system_role": True
    },
    "employee": {
        "name": "Employee",
        "description": "Self-service access only",
        "permissions": [
            Permission.LEAVE_VIEW.value, Permission.LEAVE_REQUEST.value,
            Permission.TIME_VIEW.value, Permission.TIME_CLOCK.value,
            Permission.DOCUMENTS_VIEW.value
        ],
        "is_system_role": True
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only access",
        "permissions": [
            Permission.EMPLOYEE_VIEW.value,
            Permission.PAYROLL_VIEW.value,
            Permission.LEAVE_VIEW.value,
            Permission.TIME_VIEW.value,
            Permission.DOCUMENTS_VIEW.value,
            Permission.REPORTS_VIEW.value
        ],
        "is_system_role": True
    }
}


# ==================== DATA CLASSES ====================

@dataclass
class Entity:
    """Represents a legal entity/company in multi-entity setup"""
    entity_id: str
    parent_organization_id: str  # Organization that owns multiple entities
    name: str
    legal_name: str
    registration_number: str
    country: str = "GB"
    currency: str = "GBP"
    paye_reference: Optional[str] = None
    accounts_office_reference: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "parent_organization_id": self.parent_organization_id,
            "name": self.name,
            "legal_name": self.legal_name,
            "registration_number": self.registration_number,
            "country": self.country,
            "currency": self.currency,
            "paye_reference": self.paye_reference,
            "accounts_office_reference": self.accounts_office_reference,
            "address": self.address,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Role:
    """Custom role definition"""
    role_id: str
    company_id: str
    name: str
    description: str
    permissions: List[str]
    is_system_role: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system_role": self.is_system_role,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


# ==================== ENTERPRISE SERVICE ====================

class EnterpriseService:
    """
    Enterprise features service for multi-entity and advanced RBAC.
    """
    
    def __init__(self):
        pass
    
    # ==================== RBAC ====================
    
    async def initialize_company_roles(self, company_id: str, created_by: str):
        """
        Initialize default roles for a company.
        
        Creates system roles based on templates.
        """
        now = datetime.now(timezone.utc)
        
        for role_key, template in ROLE_TEMPLATES.items():
            role = Role(
                role_id=f"role_{company_id}_{role_key}",
                company_id=company_id,
                name=template["name"],
                description=template["description"],
                permissions=template["permissions"],
                is_system_role=template["is_system_role"],
                created_at=now,
                created_by=created_by
            )
            
            # Upsert role
            await db.roles.update_one(
                {"role_id": role.role_id},
                {"$set": role.to_dict()},
                upsert=True
            )
        
        return {"status": "initialized", "roles_created": len(ROLE_TEMPLATES)}
    
    async def get_company_roles(self, company_id: str) -> List[dict]:
        """Get all roles for a company"""
        roles = await db.roles.find(
            {"company_id": company_id},
            {"_id": 0}
        ).to_list(100)
        
        return roles
    
    async def create_custom_role(
        self,
        company_id: str,
        name: str,
        description: str,
        permissions: List[str],
        created_by: str
    ) -> Role:
        """Create a custom role"""
        # Validate permissions
        valid_permissions = {p.value for p in Permission}
        invalid = set(permissions) - valid_permissions
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")
        
        role = Role(
            role_id=f"role_{uuid.uuid4().hex[:12]}",
            company_id=company_id,
            name=name,
            description=description,
            permissions=permissions,
            is_system_role=False,
            created_by=created_by
        )
        
        await db.roles.insert_one(role.to_dict())
        
        return role
    
    async def update_role_permissions(
        self,
        role_id: str,
        company_id: str,
        permissions: List[str],
        updated_by: str
    ) -> dict:
        """Update permissions for a role"""
        role = await db.roles.find_one(
            {"role_id": role_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.get("is_system_role"):
            raise ValueError("Cannot modify system role permissions")
        
        # Validate permissions
        valid_permissions = {p.value for p in Permission}
        invalid = set(permissions) - valid_permissions
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")
        
        now = datetime.now(timezone.utc)
        
        await db.roles.update_one(
            {"role_id": role_id},
            {"$set": {
                "permissions": permissions,
                "updated_at": now.isoformat(),
                "updated_by": updated_by
            }}
        )
        
        return {"status": "updated", "role_id": role_id}
    
    async def delete_custom_role(
        self,
        role_id: str,
        company_id: str
    ) -> dict:
        """Delete a custom role"""
        role = await db.roles.find_one(
            {"role_id": role_id, "company_id": company_id},
            {"_id": 0}
        )
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.get("is_system_role"):
            raise ValueError("Cannot delete system role")
        
        # Check if any users have this role
        users_with_role = await db.users.count_documents({"role": role_id})
        if users_with_role > 0:
            raise ValueError(f"Cannot delete role: {users_with_role} users have this role")
        
        await db.roles.delete_one({"role_id": role_id})
        
        return {"status": "deleted", "role_id": role_id}
    
    async def check_user_permission(
        self,
        user_id: str,
        permission: str,
        company_id: str
    ) -> bool:
        """Check if a user has a specific permission"""
        user = await db.users.find_one(
            {"user_id": user_id, "company_id": company_id},
            {"_id": 0, "role": 1}
        )
        
        if not user:
            return False
        
        role = user.get("role", "employee")
        
        # Check if it's a template role or custom role
        if role in ROLE_TEMPLATES:
            return permission in ROLE_TEMPLATES[role]["permissions"]
        
        # Check custom role
        role_doc = await db.roles.find_one(
            {"role_id": role, "company_id": company_id},
            {"_id": 0, "permissions": 1}
        )
        
        if role_doc:
            return permission in role_doc.get("permissions", [])
        
        return False
    
    async def get_user_permissions(
        self,
        user_id: str,
        company_id: str
    ) -> Set[str]:
        """Get all permissions for a user"""
        user = await db.users.find_one(
            {"user_id": user_id, "company_id": company_id},
            {"_id": 0, "role": 1}
        )
        
        if not user:
            return set()
        
        role = user.get("role", "employee")
        
        # Check if it's a template role
        if role in ROLE_TEMPLATES:
            return set(ROLE_TEMPLATES[role]["permissions"])
        
        # Check custom role
        role_doc = await db.roles.find_one(
            {"role_id": role, "company_id": company_id},
            {"_id": 0, "permissions": 1}
        )
        
        if role_doc:
            return set(role_doc.get("permissions", []))
        
        return set()
    
    # ==================== MULTI-ENTITY ====================
    
    async def create_organization(
        self,
        name: str,
        owner_user_id: str
    ) -> dict:
        """
        Create a parent organization for multi-entity setup.
        
        Organizations can have multiple legal entities under them.
        """
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        organization = {
            "organization_id": org_id,
            "name": name,
            "owner_user_id": owner_user_id,
            "entities": [],
            "settings": {
                "consolidated_reporting": True,
                "shared_employee_portal": True,
                "unified_compliance": True
            },
            "created_at": now.isoformat()
        }
        
        await db.organizations.insert_one(organization)
        
        # Update user with org access
        await db.users.update_one(
            {"user_id": owner_user_id},
            {"$set": {
                "organization_id": org_id,
                "organization_role": "owner"
            }}
        )
        
        return {"organization_id": org_id, "status": "created"}
    
    async def add_entity_to_organization(
        self,
        organization_id: str,
        entity_data: dict,
        created_by: str
    ) -> Entity:
        """
        Add a new legal entity to an organization.
        """
        # Verify organization exists
        org = await db.organizations.find_one(
            {"organization_id": organization_id},
            {"_id": 0}
        )
        
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        entity = Entity(
            entity_id=f"entity_{uuid.uuid4().hex[:12]}",
            parent_organization_id=organization_id,
            name=entity_data.get("name"),
            legal_name=entity_data.get("legal_name"),
            registration_number=entity_data.get("registration_number"),
            country=entity_data.get("country", "GB"),
            currency=entity_data.get("currency", "GBP"),
            paye_reference=entity_data.get("paye_reference"),
            accounts_office_reference=entity_data.get("accounts_office_reference"),
            address=entity_data.get("address")
        )
        
        # Create entity document
        await db.entities.insert_one(entity.to_dict())
        
        # Update organization
        await db.organizations.update_one(
            {"organization_id": organization_id},
            {"$push": {"entities": entity.entity_id}}
        )
        
        # Create corresponding company record for compatibility
        company = {
            "company_id": entity.entity_id,
            "organization_id": organization_id,
            "company_name": entity.name,
            "legal_name": entity.legal_name,
            "registration_number": entity.registration_number,
            "country": entity.country,
            "paye_reference": entity.paye_reference,
            "accounts_office_reference": entity.accounts_office_reference,
            "address": entity.address,
            "is_entity": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.companies.insert_one(company)
        
        # Initialize roles for the entity
        await self.initialize_company_roles(entity.entity_id, created_by)
        
        return entity
    
    async def get_organization_entities(
        self,
        organization_id: str
    ) -> List[dict]:
        """Get all entities in an organization"""
        entities = await db.entities.find(
            {"parent_organization_id": organization_id},
            {"_id": 0}
        ).to_list(100)
        
        return entities
    
    async def get_consolidated_payroll_summary(
        self,
        organization_id: str,
        period: str  # e.g., "2026-01"
    ) -> dict:
        """
        Get consolidated payroll summary across all entities.
        """
        entities = await self.get_organization_entities(organization_id)
        entity_ids = [e["entity_id"] for e in entities]
        
        # Get pay runs for all entities in the period
        pay_runs = await db.pay_runs.find(
            {
                "company_id": {"$in": entity_ids},
                "period": {"$regex": f"^{period}"}
            },
            {"_id": 0}
        ).to_list(1000)
        
        # Calculate totals
        total_gross = sum(pr.get("total_gross", 0) for pr in pay_runs)
        total_net = sum(pr.get("total_net", 0) for pr in pay_runs)
        total_tax = sum(pr.get("total_tax", 0) for pr in pay_runs)
        total_ni = sum(pr.get("total_ni", 0) for pr in pay_runs)
        total_employer_ni = sum(pr.get("total_employer_ni", 0) for pr in pay_runs)
        total_employees = sum(pr.get("employee_count", 0) for pr in pay_runs)
        
        # Per-entity breakdown
        entity_breakdown = []
        for entity in entities:
            entity_runs = [pr for pr in pay_runs if pr.get("company_id") == entity["entity_id"]]
            entity_breakdown.append({
                "entity_id": entity["entity_id"],
                "entity_name": entity["name"],
                "total_gross": sum(pr.get("total_gross", 0) for pr in entity_runs),
                "total_net": sum(pr.get("total_net", 0) for pr in entity_runs),
                "employee_count": sum(pr.get("employee_count", 0) for pr in entity_runs),
                "pay_runs_count": len(entity_runs)
            })
        
        return {
            "organization_id": organization_id,
            "period": period,
            "consolidated_totals": {
                "total_gross": total_gross,
                "total_net": total_net,
                "total_tax": total_tax,
                "total_ni": total_ni,
                "total_employer_ni": total_employer_ni,
                "total_employees": total_employees,
                "total_cost": total_gross + total_employer_ni
            },
            "entity_breakdown": entity_breakdown,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ==================== SCIM PROVISIONING ====================
    
    async def scim_create_user(
        self,
        company_id: str,
        scim_user: dict
    ) -> dict:
        """
        Create user from SCIM provisioning request.
        
        Supports SCIM 2.0 schema.
        """
        # Extract user data from SCIM format
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        name = scim_user.get("name", {})
        emails = scim_user.get("emails", [])
        primary_email = next((e["value"] for e in emails if e.get("primary")), emails[0]["value"] if emails else None)
        
        user = {
            "user_id": user_id,
            "company_id": company_id,
            "email": primary_email,
            "name": f"{name.get('givenName', '')} {name.get('familyName', '')}".strip(),
            "first_name": name.get("givenName"),
            "last_name": name.get("familyName"),
            "role": "employee",
            "status": "active" if scim_user.get("active", True) else "inactive",
            "scim_external_id": scim_user.get("externalId"),
            "scim_user_name": scim_user.get("userName"),
            "provisioned_via": "scim",
            "created_at": now.isoformat()
        }
        
        await db.users.insert_one(user)
        
        # Return SCIM response format
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user_id,
            "externalId": scim_user.get("externalId"),
            "userName": primary_email,
            "name": name,
            "emails": emails,
            "active": user["status"] == "active",
            "meta": {
                "resourceType": "User",
                "created": now.isoformat(),
                "lastModified": now.isoformat()
            }
        }
    
    async def scim_update_user(
        self,
        user_id: str,
        company_id: str,
        scim_user: dict
    ) -> dict:
        """Update user from SCIM request"""
        now = datetime.now(timezone.utc)
        
        name = scim_user.get("name", {})
        emails = scim_user.get("emails", [])
        primary_email = next((e["value"] for e in emails if e.get("primary")), emails[0]["value"] if emails else None)
        
        update_data = {
            "email": primary_email,
            "name": f"{name.get('givenName', '')} {name.get('familyName', '')}".strip(),
            "first_name": name.get("givenName"),
            "last_name": name.get("familyName"),
            "status": "active" if scim_user.get("active", True) else "inactive",
            "updated_at": now.isoformat()
        }
        
        result = await db.users.update_one(
            {"user_id": user_id, "company_id": company_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"User {user_id} not found")
        
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user_id,
            "userName": primary_email,
            "active": update_data["status"] == "active",
            "meta": {
                "lastModified": now.isoformat()
            }
        }
    
    async def scim_delete_user(
        self,
        user_id: str,
        company_id: str
    ) -> dict:
        """Deactivate user from SCIM delete request"""
        now = datetime.now(timezone.utc)
        
        # Soft delete - deactivate instead of removing
        result = await db.users.update_one(
            {"user_id": user_id, "company_id": company_id},
            {"$set": {
                "status": "deactivated",
                "deactivated_at": now.isoformat(),
                "deactivated_via": "scim"
            }}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"User {user_id} not found")
        
        return {"status": "deactivated", "user_id": user_id}
    
    # ==================== SAML SSO ====================
    
    async def configure_saml_sso(
        self,
        company_id: str,
        config: dict
    ) -> dict:
        """
        Configure SAML SSO settings for a company.
        
        Stores IdP metadata and configuration.
        """
        now = datetime.now(timezone.utc)
        
        sso_config = {
            "company_id": company_id,
            "sso_type": "saml",
            "enabled": config.get("enabled", False),
            "idp_entity_id": config.get("idp_entity_id"),
            "idp_sso_url": config.get("idp_sso_url"),
            "idp_slo_url": config.get("idp_slo_url"),
            "idp_certificate": config.get("idp_certificate"),
            "sp_entity_id": f"https://realtouchhr.com/saml/{company_id}",
            "sp_acs_url": f"https://realtouchhr.com/api/auth/saml/acs/{company_id}",
            "attribute_mapping": config.get("attribute_mapping", {
                "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
            }),
            "default_role": config.get("default_role", "employee"),
            "auto_provision": config.get("auto_provision", True),
            "updated_at": now.isoformat()
        }
        
        await db.sso_configs.update_one(
            {"company_id": company_id},
            {"$set": sso_config},
            upsert=True
        )
        
        return {
            "status": "configured",
            "sp_entity_id": sso_config["sp_entity_id"],
            "sp_acs_url": sso_config["sp_acs_url"]
        }
    
    async def get_sso_config(self, company_id: str) -> Optional[dict]:
        """Get SSO configuration for a company"""
        config = await db.sso_configs.find_one(
            {"company_id": company_id},
            {"_id": 0, "idp_certificate": 0}  # Don't expose certificate in API
        )
        return config


# Singleton instance
enterprise_service = EnterpriseService()
