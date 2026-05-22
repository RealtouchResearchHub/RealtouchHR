"""
Shared audit + notification + email helpers used by multiple route modules.
Extracted from server.py during the iter-13 refactor.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
import os

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
logger = logging.getLogger(__name__)


async def create_audit_entry(
    company_id: str,
    user_id: str,
    user_name: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict,
    reason: Optional[str] = None,
):
    """Insert an audit_log entry. Used by all routes for compliance trails."""
    audit = {
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": user_id,
        "user_name": user_name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.audit_log.insert_one(audit)
    return audit


async def create_notification(
    company_id: str,
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
):
    """Create an in-app notification."""
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        "user_id": user_id,
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.notifications.insert_one(notification)
    return notification
