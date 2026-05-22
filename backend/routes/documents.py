"""
RealtouchHR - Document Management Routes
Extracted from server.py during iter-13 refactor.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import uuid
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(tags=["Documents"])


class DocumentCreate(BaseModel):
    employee_id: Optional[str] = None
    name: str
    doc_type: str
    content: Optional[str] = None


class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_id: str
    company_id: str
    employee_id: Optional[str] = None
    name: str
    doc_type: str
    content: Optional[str] = None
    status: str = "draft"
    created_by: str
    created_at: datetime
    updated_at: datetime


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
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**user_doc)


@router.post("/documents", response_model=Document)
async def create_document(data: DocumentCreate, user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "document_id": document_id,
        "company_id": user.company_id,
        "employee_id": data.employee_id,
        "name": data.name,
        "doc_type": data.doc_type,
        "content": data.content,
        "status": "draft",
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.documents.insert_one(doc)

    from services.audit_service import create_audit_entry
    await create_audit_entry(
        company_id=user.company_id, user_id=user.user_id, user_name=user.name,
        action="create", entity_type="document", entity_id=document_id,
        details={"name": data.name}
    )

    doc["created_at"] = now
    doc["updated_at"] = now
    return Document(**doc)


@router.get("/documents", response_model=List[Document])
async def get_documents(user: CurrentUser = Depends(get_current_user)):
    if not user.company_id:
        return []
    docs = await db.documents.find({"company_id": user.company_id}, {"_id": 0}).to_list(1000)
    for doc in docs:
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
    return [Document(**doc) for doc in docs]
