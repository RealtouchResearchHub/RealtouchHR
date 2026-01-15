"""
RealtouchHR - Routes Package
All API route modules
"""
from .auth import router as auth_router, get_current_user, require_admin, require_hr, require_payroll
from .self_service import router as self_service_router
from .hmrc import router as hmrc_router

__all__ = [
    "auth_router",
    "self_service_router", 
    "hmrc_router",
    "get_current_user",
    "require_admin",
    "require_hr",
    "require_payroll"
]
