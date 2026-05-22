"""
RealtouchHR - Two-Factor Authentication (TOTP) Routes
- Setup: generates a TOTP secret + QR code (otpauth://) for the user to scan with Authenticator
- Verify-setup: validates first code + enables 2FA + generates 10 backup codes
- Disable: turn 2FA off (requires current TOTP code)
- Login-step: verify a TOTP code mid-login (called from /auth/login when 2FA enabled)
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, sys, uuid, io, base64, secrets, hashlib, jwt
import pyotp
import qrcode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7
TOTP_ISSUER = os.environ.get('TOTP_ISSUER', 'RealtouchHR')

router = APIRouter(prefix="/2fa", tags=["Two-Factor Authentication"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


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
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


# -------------- Helpers --------------

def _hash_backup(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_backup_codes(n: int = 10) -> List[str]:
    codes = []
    for _ in range(n):
        # 10-char alphanumeric (uppercase) — safe for paper printout
        c = secrets.token_hex(5).upper()
        codes.append(c)
    return codes


def _qr_png_base64(otp_uri: str) -> str:
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ==================== STATUS ====================

@router.get("/status")
async def status(user: CurrentUser = Depends(get_current_user)):
    rec = await db.user_2fa.find_one({"user_id": user.user_id}, {"_id": 0, "totp_secret": 0, "backup_codes_hashed": 0})
    if not rec:
        return {"enabled": False}
    return {
        "enabled": rec.get("enabled", False),
        "enrolled_at": rec.get("enrolled_at"),
        "backup_codes_remaining": rec.get("backup_codes_remaining", 0),
    }


# ==================== SETUP ====================

@router.post("/setup/begin")
async def setup_begin(user: CurrentUser = Depends(get_current_user)):
    """
    Step 1: Generate a TOTP secret. Returns a QR code (base64 PNG) + otpauth URI.
    The user adds this to their authenticator app, then calls /setup/verify.
    """
    secret = pyotp.random_base32()
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=TOTP_ISSUER)

    # Store secret as 'pending' (not yet enabled)
    await db.user_2fa.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "user_id": user.user_id,
            "email": user.email,
            "totp_secret": secret,
            "enabled": False,
            "pending_setup": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {
        "otp_uri": otp_uri,
        "secret": secret,  # show once so user can manually type if needed
        "qr_png_base64": _qr_png_base64(otp_uri),
        "issuer": TOTP_ISSUER,
    }


class VerifySetupBody(BaseModel):
    code: str


@router.post("/setup/verify")
async def setup_verify(body: VerifySetupBody, user: CurrentUser = Depends(get_current_user)):
    """Step 2: User enters first 6-digit code. We enable 2FA + return one-time backup codes."""
    rec = await db.user_2fa.find_one({"user_id": user.user_id}, {"_id": 0})
    if not rec or not rec.get("totp_secret"):
        raise HTTPException(status_code=400, detail="No 2FA setup in progress")

    totp = pyotp.TOTP(rec["totp_secret"])
    if not totp.verify(body.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")

    backup_codes = _generate_backup_codes(10)
    backup_hashed = [_hash_backup(c) for c in backup_codes]

    await db.user_2fa.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "enabled": True,
            "pending_setup": False,
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "backup_codes_hashed": backup_hashed,
            "backup_codes_remaining": len(backup_hashed),
        }}
    )
    await db.users.update_one({"user_id": user.user_id}, {"$set": {"totp_enabled": True}})

    return {
        "enabled": True,
        "backup_codes": backup_codes,
        "message": "2FA enabled. Save your backup codes in a safe place — each can be used once.",
    }


# ==================== DISABLE ====================

class DisableBody(BaseModel):
    code: str


@router.post("/disable")
async def disable(body: DisableBody, user: CurrentUser = Depends(get_current_user)):
    rec = await db.user_2fa.find_one({"user_id": user.user_id}, {"_id": 0})
    if not rec or not rec.get("enabled"):
        raise HTTPException(status_code=400, detail="2FA not enabled")

    # Verify either a current TOTP code or an unused backup code
    code = (body.code or "").strip()
    valid = False
    totp = pyotp.TOTP(rec["totp_secret"])
    if totp.verify(code, valid_window=1):
        valid = True
    else:
        # backup code
        hashed = _hash_backup(code.upper())
        if hashed in (rec.get("backup_codes_hashed") or []):
            valid = True

    if not valid:
        raise HTTPException(status_code=400, detail="Invalid code")

    await db.user_2fa.delete_one({"user_id": user.user_id})
    await db.users.update_one({"user_id": user.user_id}, {"$unset": {"totp_enabled": ""}})
    return {"enabled": False, "message": "2FA disabled"}


# ==================== LOGIN STEP-2 ====================

class LoginVerifyBody(BaseModel):
    pending_token: str  # short-lived token issued by /auth/login when 2FA required
    code: str           # 6-digit TOTP or backup code


@router.post("/login/verify")
async def login_verify(body: LoginVerifyBody, response: Response):
    """
    Second step in login flow when 2FA is enabled.
    Frontend gets `pending_token` from /auth/login, then submits the user's TOTP/backup code here.
    On success: issues the real JWT session.
    """
    # Decode the pending token
    try:
        payload = jwt.decode(body.pending_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired pending token")

    if payload.get("stage") != "2fa_pending":
        raise HTTPException(status_code=400, detail="Not a 2FA pending token")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Malformed pending token")

    rec = await db.user_2fa.find_one({"user_id": user_id}, {"_id": 0})
    if not rec or not rec.get("enabled"):
        raise HTTPException(status_code=400, detail="2FA not enabled for this user")

    code = (body.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code required")

    totp = pyotp.TOTP(rec["totp_secret"])
    valid = False
    used_backup = False
    if totp.verify(code, valid_window=1):
        valid = True
    else:
        # backup code
        hashed = _hash_backup(code.upper())
        if hashed in (rec.get("backup_codes_hashed") or []):
            valid = True
            used_backup = True
            new_list = [h for h in rec["backup_codes_hashed"] if h != hashed]
            await db.user_2fa.update_one(
                {"user_id": user_id},
                {"$set": {"backup_codes_hashed": new_list, "backup_codes_remaining": len(new_list)}}
            )

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid code")

    # Issue real session
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    real_payload = {
        "user_id": user_id,
        "email": user_doc["email"],
        "exp": now + timedelta(days=JWT_EXPIRATION_DAYS),
    }
    token = jwt.encode(real_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat(),
        "via_2fa": True,
    })

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60,
    )
    user_doc.pop("password_hash", None)
    user_doc.pop("totp_secret", None)
    user_doc["created_at"] = user_doc.get("created_at")
    return {
        "token": token,
        "user": user_doc,
        "used_backup_code": used_backup,
    }
