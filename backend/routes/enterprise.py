"""
RealtouchHR - Enterprise Routes
Multi-entity Payroll, Advanced RBAC, SCIM/SAML SSO

Enterprise-grade features for larger organizations.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise", tags=["Enterprise Features"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None
    organization_id: Optional[str] = None


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=10, max_length=200)
    permissions: List[str]


class UpdateRolePermissionsRequest(BaseModel):
    permissions: List[str]


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class CreateEntityRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    legal_name: str = Field(..., min_length=2, max_length=200)
    registration_number: str
    country: str = "GB"
    currency: str = "GBP"
    paye_reference: Optional[str] = None
    accounts_office_reference: Optional[str] = None
    address: Optional[Dict[str, str]] = None


class SAMLConfigRequest(BaseModel):
    enabled: bool = False
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_slo_url: Optional[str] = None
    idp_certificate: Optional[str] = None
    attribute_mapping: Optional[Dict[str, str]] = None
    default_role: str = "employee"
    auto_provision: bool = True


# ==================== AUTH HELPERS ====================

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
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def require_owner(request: Request) -> User:
    """Require owner role"""
    user = await get_current_user(request)
    if user.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only Owner can access enterprise features"
        )
    return user


async def require_admin(request: Request) -> User:
    """Require admin or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin or Owner access required"
        )
    return user


# ==================== RBAC ROUTES ====================

@router.get("/roles")
async def list_roles(user: User = Depends(require_admin)):
    """
    List all roles for the company.
    
    Includes system roles and custom roles.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    roles = await enterprise_service.get_company_roles(user.company_id)
    
    return {
        "roles": roles,
        "total": len(roles)
    }


@router.post("/roles")
async def create_custom_role(
    role_request: CreateRoleRequest,
    user: User = Depends(require_owner)
):
    """
    Create a custom role with specific permissions.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        role = await enterprise_service.create_custom_role(
            user.company_id,
            role_request.name,
            role_request.description,
            role_request.permissions,
            user.user_id
        )
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    update_request: UpdateRolePermissionsRequest,
    user: User = Depends(require_owner)
):
    """
    Update permissions for a custom role.
    
    Cannot modify system roles.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.update_role_permissions(
            role_id,
            user.company_id,
            update_request.permissions,
            user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}")
async def delete_custom_role(
    role_id: str,
    user: User = Depends(require_owner)
):
    """
    Delete a custom role.
    
    Cannot delete system roles or roles assigned to users.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.delete_custom_role(role_id, user.company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions")
async def list_all_permissions(user: User = Depends(require_admin)):
    """
    List all available permissions.
    
    Useful for building role management UI.
    """
    from services.enterprise_service import Permission
    
    permissions_by_category = {}
    
    for perm in Permission:
        category = perm.value.split(":")[0]
        if category not in permissions_by_category:
            permissions_by_category[category] = []
        permissions_by_category[category].append({
            "code": perm.value,
            "name": perm.name.replace("_", " ").title()
        })
    
    return {
        "permissions": permissions_by_category,
        "total": len(Permission)
    }


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    user: User = Depends(require_admin)
):
    """
    Get all permissions for a specific user.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    permissions = await enterprise_service.get_user_permissions(user_id, user.company_id)
    
    return {
        "user_id": user_id,
        "permissions": list(permissions),
        "total": len(permissions)
    }


# ==================== MULTI-ENTITY ROUTES ====================

@router.post("/organizations")
async def create_organization(
    org_request: CreateOrganizationRequest,
    user: User = Depends(require_owner)
):
    """
    Create a parent organization for multi-entity management.
    
    Allows managing multiple legal entities under one organization.
    """
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.create_organization(
            org_request.name,
            user.user_id
        )
        return result
    except Exception as e:
        logger.error(f"Organization creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizations/{organization_id}/entities")
async def list_organization_entities(
    organization_id: str,
    user: User = Depends(require_owner)
):
    """
    List all entities in an organization.
    """
    from services.enterprise_service import enterprise_service
    
    # Verify user has access to organization
    org = await db.organizations.find_one(
        {"organization_id": organization_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org.get("owner_user_id") != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    entities = await enterprise_service.get_organization_entities(organization_id)
    
    return {
        "organization_id": organization_id,
        "organization_name": org.get("name"),
        "entities": entities,
        "total": len(entities)
    }


@router.post("/organizations/{organization_id}/entities")
async def add_entity(
    organization_id: str,
    entity_request: CreateEntityRequest,
    user: User = Depends(require_owner)
):
    """
    Add a new legal entity to an organization.
    """
    from services.enterprise_service import enterprise_service
    
    # Verify user has access to organization
    org = await db.organizations.find_one(
        {"organization_id": organization_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org.get("owner_user_id") != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        entity = await enterprise_service.add_entity_to_organization(
            organization_id,
            entity_request.dict(),
            user.user_id
        )
        return entity.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/organizations/{organization_id}/payroll-summary")
async def get_consolidated_payroll(
    organization_id: str,
    period: str,
    user: User = Depends(require_owner)
):
    """
    Get consolidated payroll summary across all entities.
    
    Period format: YYYY-MM (e.g., 2026-01)
    """
    from services.enterprise_service import enterprise_service
    
    # Verify user has access to organization
    org = await db.organizations.find_one(
        {"organization_id": organization_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org.get("owner_user_id") != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        summary = await enterprise_service.get_consolidated_payroll_summary(
            organization_id,
            period
        )
        return summary
    except Exception as e:
        logger.error(f"Consolidated payroll error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SSO ROUTES ====================

@router.get("/sso/config")
async def get_sso_configuration(user: User = Depends(require_owner)):
    """
    Get SSO configuration for the company.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    config = await enterprise_service.get_sso_config(user.company_id)
    
    if not config:
        return {
            "configured": False,
            "message": "SSO not configured"
        }
    
    return {
        "configured": True,
        "config": config
    }


@router.put("/sso/saml")
async def configure_saml_sso(
    saml_config: SAMLConfigRequest,
    user: User = Depends(require_owner)
):
    """
    Configure SAML SSO for the company.
    
    Requires IdP metadata from your identity provider.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.configure_saml_sso(
            user.company_id,
            saml_config.dict()
        )
        return result
    except Exception as e:
        logger.error(f"SAML configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SCIM ROUTES ====================
# Note: These would typically be called by an IdP, not directly

@router.post("/scim/Users")
async def scim_create_user(
    scim_user: dict,
    user: User = Depends(require_admin)
):
    """
    SCIM 2.0 User creation endpoint.
    
    Used by Identity Providers for automated user provisioning.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.scim_create_user(user.company_id, scim_user)
        return result
    except Exception as e:
        logger.error(f"SCIM create user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scim/Users/{scim_user_id}")
async def scim_update_user(
    scim_user_id: str,
    scim_user: dict,
    user: User = Depends(require_admin)
):
    """
    SCIM 2.0 User update endpoint.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.scim_update_user(scim_user_id, user.company_id, scim_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/scim/Users/{scim_user_id}")
async def scim_delete_user(
    scim_user_id: str,
    user: User = Depends(require_admin)
):
    """
    SCIM 2.0 User deletion endpoint.
    
    Performs soft delete (deactivation).
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.enterprise_service import enterprise_service
    
    try:
        result = await enterprise_service.scim_delete_user(scim_user_id, user.company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== AUDIT ROUTES ====================

@router.get("/audit-log")
async def get_enterprise_audit_log(
    entity_type: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(require_admin)
):
    """
    Get enterprise audit log.
    
    Filter by entity_type: user, employee, payroll, role, etc.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    query = {"company_id": user.company_id}
    if entity_type:
        query["entity_type"] = entity_type
    
    audit_entries = await db.audit_log.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "audit_entries": audit_entries,
        "total": len(audit_entries)
    }
