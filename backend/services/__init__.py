"""
RealtouchHR - Services Package
Business logic and external service integrations
"""
from .email_service import email_service, EmailService
from .hmrc_service import hmrc_service, HMRCService, RTIValidator

__all__ = [
    "email_service",
    "EmailService", 
    "hmrc_service",
    "HMRCService",
    "RTIValidator"
]
