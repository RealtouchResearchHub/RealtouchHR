"""Trial status + download gating routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os, sys, jwt
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/trial", tags=["Trial"])


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None


def _normalize_current_user_doc(user_doc: dict) -> dict:
    normalized = dict(user_doc)
    email = (normalized.get("email") or "").strip()
    normalized["name"] = (normalized.get("name") or email.split("@")[0] or "User").strip()
    return normalized


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
    return CurrentUser(**_normalize_current_user_doc(user_doc))


@router.get("/status")
async def get_trial_status(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    from services.trial_service import trial_service
    return await trial_service.get_trial_status(user.company_id)


@router.post("/start")
async def start_trial(user: CurrentUser = Depends(get_current_user)):
    """Idempotent: start a 14-day trial for the current company"""
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can start trial")
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    from services.trial_service import trial_service
    return await trial_service.start_trial(user.company_id)


@router.get("/download-access/{resource_type}/{resource_id}")
async def check_download_access(
    resource_type: str,
    resource_id: str,
    user: CurrentUser = Depends(get_current_user)
):
    """Check whether the user can download — used by frontend to decide
    whether to fetch the PDF or show the payment modal."""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company")
    from services.trial_service import download_gate
    return await download_gate.check_access(user.company_id, user.user_id, resource_id)
