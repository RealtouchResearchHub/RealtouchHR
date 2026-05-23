"""
RealtouchHR - Tenant Suspension Middleware
Blocks API requests from users whose company is suspended or unpaid.
Allows: auth, billing read, checkout (so they can resubscribe), webhooks, health, super-admin (platform owner).
"""
import os
import sys
import jwt
import logging
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

logger = logging.getLogger(__name__)


# Paths that are ALWAYS allowed (even when tenant is suspended)
ALLOWED_PATH_PREFIXES = (
    "/api/auth/",          # login, logout, register, password reset, me
    "/api/payments/billing",       # see current state
    "/api/payments/checkout/",     # subscribe/upgrade (path to resolve suspension)
    "/api/payments/portal",        # customer portal
    "/api/payments/webhook",       # Stripe webhooks
    "/api/payments/plans",         # see plans
    "/api/payments/transactions",  # see receipts
    "/api/payments/poll",          # poll checkout status
    "/api/super-admin/",   # platform admin can do anything
    "/api/health",
    "/api/2fa/",           # 2FA flows
    "/api/trust-badge/",   # public verification surface
    "/api/demo/",          # public landing demo endpoints
)


class TenantSuspensionMiddleware(BaseHTTPMiddleware):
    """
    Block requests from suspended companies.
    
    Suspension reasons (set on company doc):
      - suspended=True : platform admin suspended the tenant (any reason)
      - subscription_status='past_due' / 'unpaid' / 'canceled' : Stripe says billing failed
    
    Trial users are NOT suspended.
    """

    def __init__(self, app, db_name: str = None):
        super().__init__(app)
        mongo_url = os.environ.get('MONGO_URL')
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name or os.environ.get('DB_NAME')]

    async def dispatch(self, request, call_next):
        path = request.url.path

        # Pass through non-API requests and allowed paths
        if not path.startswith("/api/"):
            return await call_next(request)
        for prefix in ALLOWED_PATH_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Try to read the auth token
        token = request.cookies.get("session_token")
        if not token:
            auth = request.headers.get("Authorization") or ""
            if auth.startswith("Bearer "):
                token = auth.split(" ")[1]
        if not token:
            return await call_next(request)  # let downstream auth handle 401

        try:
            user_id = None
            session = await self.db.user_sessions.find_one({"session_token": token}, {"_id": 0, "user_id": 1})
            if session:
                user_id = session.get("user_id")
            else:
                try:
                    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                    user_id = payload.get("user_id")
                except jwt.PyJWTError:
                    return await call_next(request)

            if not user_id:
                return await call_next(request)

            user = await self.db.users.find_one(
                {"user_id": user_id},
                {"_id": 0, "company_id": 1, "is_platform_admin": 1, "email": 1}
            )
            if not user:
                return await call_next(request)

            # Platform admins are never suspended
            if user.get("is_platform_admin"):
                return await call_next(request)

            company_id = user.get("company_id")
            if not company_id:
                return await call_next(request)

            company = await self.db.companies.find_one(
                {"company_id": company_id},
                {"_id": 0, "suspended": 1, "suspended_reason": 1, "subscription_status": 1, "name": 1}
            )
            if not company:
                return await call_next(request)

            # Block if suspended
            if company.get("suspended") is True:
                return JSONResponse(
                    status_code=423,  # 423 Locked
                    content={
                        "detail": "Your company account has been suspended by the platform administrator.",
                        "reason": company.get("suspended_reason") or "No reason provided",
                        "company_name": company.get("name"),
                        "tenant_status": "suspended",
                        "contact": "Please contact support to restore access.",
                    },
                )

            # Block if subscription is in a hard-failed state
            sub_status = (company.get("subscription_status") or "").lower()
            if sub_status in ("past_due", "unpaid", "canceled"):
                return JSONResponse(
                    status_code=402,  # 402 Payment Required
                    content={
                        "detail": f"Your subscription is {sub_status}. Please update your payment method to restore access.",
                        "tenant_status": sub_status,
                        "action": "Visit /billing to update payment.",
                    },
                )

        except Exception as exc:
            logger.warning(f"TenantSuspensionMiddleware: error {exc}")
            # On error, fail-open to avoid locking everyone out

        return await call_next(request)
