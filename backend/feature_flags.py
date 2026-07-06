"""
RealtouchHR - Payroll / RTI / Pension safety feature flags

These flags gate anything that could look like a live HMRC RTI submission or
a live pension provider submission. Defaults are intentionally conservative:
nothing here claims to be "live" until a real embedded payroll provider or
HMRC Gateway integration is connected and explicitly enabled.

Resolution order for each flag: platform_feature_flags DB override (set via
Super Admin) > environment variable override > safe default below.
"""
import os
import uuid
from datetime import datetime, timezone

from database import db

DEFAULTS = {
    "payroll_native_sandbox": True,
    "payroll_embedded_provider": False,
    "live_rti_enabled": False,
    "pension_integration_enabled": False,
    "rti_legacy_hmrc_disabled": True,
}

ENV_KEYS = {
    "payroll_native_sandbox": "PAYROLL_NATIVE_SANDBOX",
    "payroll_embedded_provider": "PAYROLL_EMBEDDED_PROVIDER",
    "live_rti_enabled": "RTI_LIVE_SUBMISSION_ENABLED",
    "pension_integration_enabled": "PENSION_INTEGRATION_ENABLED",
    "rti_legacy_hmrc_disabled": "RTI_LEGACY_HMRC_DISABLED",
}


def _env_override(key: str):
    val = os.environ.get(ENV_KEYS[key])
    if val is None:
        return None
    return val.lower() == "true"


async def get_flag(key: str) -> bool:
    """Resolve a payroll/RTI/pension safety flag: DB override > env override > default."""
    try:
        doc = await db.platform_feature_flags.find_one({"flag_key": key}, {"_id": 0})
    except Exception:
        doc = None

    if doc and "global_enabled" in doc:
        return bool(doc["global_enabled"])

    env_val = _env_override(key)
    if env_val is not None:
        return env_val

    return DEFAULTS[key]


async def get_all_flags() -> dict:
    return {key: await get_flag(key) for key in DEFAULTS}


async def log_payroll_event(action: str, details: dict = None, company_id: str = None, user_id: str = None):
    """Audit-log entry for payroll/RTI/pension safety events (blocked legacy access,
    sandbox simulations, provider/flag status changes)."""
    await db.audit_log.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "action": action,
        "company_id": company_id,
        "user_id": user_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
