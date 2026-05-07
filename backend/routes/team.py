"""
RealtouchHR - Team Management Routes
Company admins/owners can invite users, assign roles, remove members.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, sys, uuid, jwt, secrets, logging
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
APP_URL = os.environ.get('APP_URL', 'https://realtouchhr.com')
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Team Management"])

VALID_ROLES = ["owner", "admin", "hr_manager", "payroll_admin", "manager", "employee", "viewer"]


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    role: str = Field(..., description="One of: admin, hr_manager, payroll_admin, manager, employee, viewer")


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str = Field(..., min_length=8)


class RoleUpdateRequest(BaseModel):
    role: str


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            token = auth.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    else:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


async def require_admin(request: Request) -> CurrentUser:
    user = await get_current_user(request)
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin only")
    return user


# ==================== USER LIST ====================

@router.get("")
async def list_company_users(user: CurrentUser = Depends(get_current_user)):
    """List all users in the current company"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    users = await db.users.find(
        {"company_id": user.company_id},
        {"_id": 0, "password_hash": 0}
    ).to_list(1000)
    return {"users": users, "total": len(users)}


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    data: RoleUpdateRequest,
    current: CurrentUser = Depends(get_current_user)
):
    """Change a user's role. Owner-only."""
    if current.role != "owner":
        raise HTTPException(status_code=403, detail="Only the company owner can change roles")
    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {VALID_ROLES}")
    if user_id == current.user_id and data.role != "owner":
        raise HTTPException(status_code=400, detail="You cannot demote yourself")

    target = await db.users.find_one(
        {"user_id": user_id, "company_id": current.company_id},
        {"_id": 0}
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this company")

    # Prevent changing another owner's role unless current is owner and they choose to
    await db.users.update_one(
        {"user_id": user_id, "company_id": current.company_id},
        {"$set": {"role": data.role, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": current.company_id,
        "user_id": current.user_id,
        "user_name": current.name,
        "action": "role_updated",
        "entity_type": "user",
        "entity_id": user_id,
        "details": {"old_role": target.get("role"), "new_role": data.role},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"Role updated to {data.role}", "user_id": user_id}


@router.delete("/{user_id}")
async def remove_user(
    user_id: str,
    current: CurrentUser = Depends(get_current_user)
):
    """Remove a user from the company. Owner-only."""
    if current.role != "owner":
        raise HTTPException(status_code=403, detail="Only the company owner can remove users")
    if user_id == current.user_id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")

    target = await db.users.find_one({"user_id": user_id, "company_id": current.company_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this company")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove another owner")

    await db.users.delete_one({"user_id": user_id, "company_id": current.company_id})
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": current.company_id,
        "user_id": current.user_id,
        "user_name": current.name,
        "action": "user_removed",
        "entity_type": "user",
        "entity_id": user_id,
        "details": {"email": target.get("email")},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "User removed"}


# ==================== INVITES ====================

@router.post("/invite")
async def invite_user(
    data: InviteRequest,
    current: CurrentUser = Depends(require_admin)
):
    """Invite a user by email + role. Creates a pending invite with a one-use token."""
    if data.role not in VALID_ROLES or data.role == "owner":
        raise HTTPException(status_code=400, detail=f"Invalid role. Use one of: {[r for r in VALID_ROLES if r != 'owner']}")
    if not current.company_id:
        raise HTTPException(status_code=400, detail="No company setup")

    # Check duplicates
    existing_user = await db.users.find_one({"email": data.email, "company_id": current.company_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email is already in your company")

    existing_invite = await db.user_invites.find_one({
        "email": data.email, "company_id": current.company_id, "status": "pending"
    })
    if existing_invite:
        raise HTTPException(status_code=400, detail="A pending invite already exists for this email")

    invite_token = secrets.token_urlsafe(32)
    invite_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)

    await db.user_invites.insert_one({
        "invite_id": invite_id,
        "invite_token": invite_token,
        "email": data.email,
        "name": data.name,
        "role": data.role,
        "company_id": current.company_id,
        "invited_by": current.user_id,
        "invited_by_name": current.name,
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    })

    # Send invite email (best-effort, honours mock mode)
    try:
        from services.email_service import email_service, get_base_template
        company = await db.companies.find_one({"company_id": current.company_id}, {"_id": 0}) or {}
        invite_link = f"{APP_URL}/invite/{invite_token}"
        html = get_base_template(f"""
            <h2 style="color: #111827; margin: 0 0 16px 0;">You're invited to {company.get('name', 'RealtouchHR')}</h2>
            <p style="color: #374151; font-size: 16px;">Hi {data.name},</p>
            <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                <strong>{current.name}</strong> has invited you to join <strong>{company.get('name', 'their team')}</strong>
                on RealtouchHR as a <strong>{data.role.replace('_', ' ').title()}</strong>.
            </p>
            <div style="margin: 24px 0;">
                <a href="{invite_link}" style="display:inline-block; background:#4f46e5; color:#fff; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:600;">
                    Accept invitation
                </a>
            </div>
            <p style="color:#6b7280; font-size:13px;">This invitation expires in 7 days.</p>
        """)
        await email_service.send_email(data.email, f"Invitation to join {company.get('name', 'RealtouchHR')}", html)
    except Exception as exc:
        logger.warning(f"Invite email failed: {exc}")

    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": current.company_id,
        "user_id": current.user_id,
        "user_name": current.name,
        "action": "user_invited",
        "entity_type": "user_invite",
        "entity_id": invite_id,
        "details": {"email": data.email, "role": data.role},
        "timestamp": now.isoformat(),
    })

    return {
        "message": "Invitation sent",
        "invite_id": invite_id,
        "invite_link": f"{APP_URL}/invite/{invite_token}",
        "expires_at": expires.isoformat(),
    }


@router.get("/invites")
async def list_invites(current: CurrentUser = Depends(require_admin)):
    """List all invites for the current company"""
    invites = await db.user_invites.find(
        {"company_id": current.company_id},
        {"_id": 0, "invite_token": 0}
    ).sort("created_at", -1).to_list(500)
    return {"invites": invites, "total": len(invites)}


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: str, current: CurrentUser = Depends(require_admin)):
    result = await db.user_invites.update_one(
        {"invite_id": invite_id, "company_id": current.company_id, "status": "pending"},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Pending invite not found")
    return {"message": "Invite revoked"}


@router.get("/invite/{token}")
async def preview_invite(token: str):
    """Public endpoint: fetch invite details by token (no auth)"""
    invite = await db.user_invites.find_one(
        {"invite_token": token, "status": "pending"},
        {"_id": 0, "invite_token": 0}
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    if datetime.fromisoformat(invite["expires_at"]).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")

    company = await db.companies.find_one({"company_id": invite["company_id"]}, {"_id": 0, "name": 1}) or {}
    return {
        "email": invite["email"],
        "name": invite["name"],
        "role": invite["role"],
        "company_name": company.get("name", "RealtouchHR"),
        "invited_by_name": invite.get("invited_by_name"),
        "expires_at": invite["expires_at"],
    }


@router.post("/invite/accept")
async def accept_invite(data: AcceptInviteRequest):
    """Public endpoint: accept invite by token + password. Creates the user account."""
    invite = await db.user_invites.find_one({"invite_token": data.invite_token, "status": "pending"}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or already-used invitation")
    if datetime.fromisoformat(invite["expires_at"]).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")

    # Safety: ensure email not already a user in ANY company
    existing = await db.users.find_one({"email": invite["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    now = datetime.now(timezone.utc)
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

    await db.users.insert_one({
        "user_id": user_id,
        "email": invite["email"],
        "name": invite["name"],
        "role": invite["role"],
        "company_id": invite["company_id"],
        "password_hash": password_hash,
        "auth_method": "password",
        "created_at": now.isoformat(),
        "preferences": {"theme_preference": "light"},
    })

    # Mark invite accepted
    await db.user_invites.update_one(
        {"invite_id": invite["invite_id"]},
        {"$set": {"status": "accepted", "accepted_at": now.isoformat(), "user_id": user_id}}
    )

    # Issue session token (24h default)
    token = jwt.encode(
        {"user_id": user_id, "email": invite["email"], "exp": now + timedelta(hours=24)},
        JWT_SECRET, algorithm="HS256"
    )
    await db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    })

    await db.audit_log.insert_one({
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": invite["company_id"],
        "user_id": user_id,
        "user_name": invite["name"],
        "action": "invite_accepted",
        "entity_type": "user",
        "entity_id": user_id,
        "details": {"email": invite["email"], "role": invite["role"]},
        "timestamp": now.isoformat(),
    })

    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "email": invite["email"],
            "name": invite["name"],
            "role": invite["role"],
            "company_id": invite["company_id"],
        }
    }
