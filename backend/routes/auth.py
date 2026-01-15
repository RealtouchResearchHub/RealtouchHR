"""
RealtouchHR - Authentication Routes
JWT and Google OAuth authentication
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from datetime import datetime, timezone, timedelta
import httpx
import logging

from models import (
    UserCreate, UserLogin, User, TokenResponse, UserRole
)
from utils import (
    db, hash_password, verify_password, create_jwt_token, 
    generate_user_id, generate_company_id, now_utc, now_iso,
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_DAYS
)
import jwt

logger = logging.getLogger(__name__)

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


@router.post("/session")
async def process_google_session(request: Request, response: Response):
    """Process Emergent Google OAuth session"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # Fetch user data from Emergent Auth
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = auth_response.json()
        except Exception as e:
            logger.error(f"Error fetching session data: {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")
    
    now = now_utc()
    
    # Check if user exists
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user_doc:
        user_id = user_doc["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        user_id = generate_user_id()
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": "owner",
            "theme_preference": "light",
            "created_at": now.isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "created_at": now.isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user_doc["user_id"] = user_id
    user_doc["name"] = name
    user_doc["picture"] = picture
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    else:
        user_doc["created_at"] = now
    
    return {"user": User(**user_doc), "token": session_token}


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
