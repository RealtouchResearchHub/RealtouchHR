"""
RealtouchHR - Authentication Routes
JWT and Google OAuth authentication
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta
import httpx
import logging
import os
import sys
import secrets
import urllib.parse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path
import bcrypt
import jwt
import uuid

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

from database import db
# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: Optional[str] = None
    role: str = "owner"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "owner"
    company_id: Optional[str] = None
    employee_id: Optional[str] = None
    theme_preference: str = "light"
    created_at: datetime

class TokenResponse(BaseModel):
    token: str
    user: User

# ==================== HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_jwt_token(user_id: str, email: str, role: str = "owner") -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"

def generate_company_id() -> str:
    return f"company_{uuid.uuid4().hex[:12]}"

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

logger = logging.getLogger(__name__)

# Google OAuth config
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
)
APP_URL = os.environ.get("APP_URL", "http://localhost:3000").rstrip("/")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> User:
    """Get current authenticated user from session or JWT token"""
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check session in database
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        # Try JWT token
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=401, detail="User not found")
            if isinstance(user_doc.get("created_at"), str):
                user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check expiry
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return User(**user_doc)


async def require_role(user: User, allowed_roles: list) -> User:
    """Check if user has required role"""
    if user.role not in allowed_roles and "*" not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin or owner role"""
    return await require_role(user, ["owner", "admin"])


async def require_hr(user: User = Depends(get_current_user)) -> User:
    """Require HR manager or above"""
    return await require_role(user, ["owner", "admin", "hr_manager"])


async def require_payroll(user: User = Depends(get_current_user)) -> User:
    """Require payroll admin or above"""
    return await require_role(user, ["owner", "admin", "payroll_admin"])


# ==================== ROUTES ====================

@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate, response: Response):
    """Register a new user with optional company creation"""
    # Check if user exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = generate_user_id()
    now = now_utc()
    
    # Create user
    user_doc = {
        "user_id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role.value if hasattr(data.role, 'value') else data.role,
        "theme_preference": "light",
        "created_at": now.isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Create company if provided
    if data.company_name:
        company_id = generate_company_id()
        company_doc = {
            "company_id": company_id,
            "name": data.company_name,
            "owner_id": user_id,
            "payroll_frequency": "monthly",
            "setup_completed": False,
            "is_parent": True,
            "created_at": now.isoformat()
        }
        await db.companies.insert_one(company_doc)
        await db.users.update_one({"user_id": user_id}, {"$set": {"company_id": company_id}})
        user_doc["company_id"] = company_id
    
    # Create session
    token = create_jwt_token(user_id, data.email, user_doc.get("role", "owner"))
    session_doc = {
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60
    )
    
    user_doc.pop("password_hash", None)
    user_doc["created_at"] = now
    return TokenResponse(token=token, user=User(**user_doc))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, response: Response):
    """Login with email and password"""
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = user_doc["user_id"]
    now = now_utc()
    
    token = create_jwt_token(user_id, data.email, user_doc.get("role", "owner"))
    session_doc = {
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60
    )
    
    user_doc.pop("password_hash", None)
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return TokenResponse(token=token, user=User(**user_doc))


@router.get("/me", response_model=User)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info"""
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out"}


@router.put("/preferences")
async def update_preferences(data: dict, user: User = Depends(get_current_user)):
    """Update user preferences"""
    update_fields = {}
    if "theme_preference" in data:
        update_fields["theme_preference"] = data["theme_preference"]

    if update_fields:
        await db.users.update_one({"user_id": user.user_id}, {"$set": update_fields})

    return {"message": "Preferences updated"}


# ==================== GOOGLE OAUTH ====================

@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": secrets.token_urlsafe(16),
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None, state: str = None):
    if error or not code:
        return RedirectResponse(url=f"{APP_URL}/login?error=google_denied")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if token_resp.status_code != 200:
        logger.error("Google token exchange failed: %s", token_resp.text)
        return RedirectResponse(url=f"{APP_URL}/login?error=google_token_failed")

    access_token = token_resp.json().get("access_token")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if info_resp.status_code != 200:
        return RedirectResponse(url=f"{APP_URL}/login?error=google_userinfo_failed")

    guser = info_resp.json()
    email = guser.get("email")
    if not email:
        return RedirectResponse(url=f"{APP_URL}/login?error=google_no_email")

    name = guser.get("name") or email.split("@")[0]
    picture = guser.get("picture")
    now = now_utc()

    # Find or create user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        user_id = generate_user_id()
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": "owner",
            "theme_preference": "light",
            "created_at": now.isoformat(),
        }
        await db.users.insert_one(user_doc)
    else:
        user_id = user_doc["user_id"]
        updates: dict = {}
        if picture and user_doc.get("picture") != picture:
            updates["picture"] = picture
        if updates:
            await db.users.update_one({"user_id": user_id}, {"$set": updates})
            user_doc.update(updates)

    # Create session
    token = create_jwt_token(user_id, email, user_doc.get("role", "owner"))
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": (now + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat(),
        "created_at": now.isoformat(),
    })

    # Redirect to frontend callback page; also set the session cookie
    redirect = RedirectResponse(url=f"{APP_URL}/auth/google/callback?token={token}")
    redirect.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=JWT_EXPIRATION_DAYS * 24 * 60 * 60,
    )
    return redirect
