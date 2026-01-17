"""
RealtouchHR - RTI Sync Engine Routes
HMRC Real Time Information Compliance API

IMPORTANT COMPLIANCE DISCLAIMERS:
- This software is RTI-compatible and HMRC-aligned
- HMRC does not endorse, approve, or certify payroll software
- Compliance is the employer's legal responsibility
- This tool enables compliance through accurate record-keeping and timely submissions
- All submissions require explicit human approval
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import jwt

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rti-sync", tags=["RTI Sync Engine"])


# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "owner"
    company_id: Optional[str] = None

class PrepareSubmissionRequest(BaseModel):
    payrun_id: str

class ApprovalRequest(BaseModel):
    confirmation_text: str = Field(
        ...,
        description="Must be exactly: 'I confirm submission {submission_id}'"
    )

class RejectionRequest(BaseModel):
    reason: str = Field(..., min_length=10, description="Reason for rejection (min 10 chars)")

class SubmitRequest(BaseModel):
    acknowledge_disclaimer: bool = Field(
        ...,
        description="Must acknowledge HMRC compliance disclaimer"
    )


# ==================== AUTH HELPERS ====================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

async def get_current_user(request: Request) -> User:
    """Get current authenticated user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=401, detail="User not found")
            return User(**user_doc)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)

async def require_payroll_admin(request: Request) -> User:
    """Require payroll admin or owner role"""
    user = await get_current_user(request)
    if user.role not in ["owner", "admin", "payroll_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only Payroll Admin or Owner can manage RTI submissions"
        )
    return user


# ==================== CONFIGURATION ROUTES ====================

@router.get("/status")
async def get_rti_sync_status(user: User = Depends(get_current_user)):
    """
    Get RTI Sync Engine status and configuration.
    
    Shows current mode (Sandbox/Live/Paused), feature flags, and company setup status.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rti_sync_service import rti_sync_engine, get_company_rti_settings
    
    settings = await get_company_rti_settings(user.company_id)
    
    return {
        "engine_mode": rti_sync_engine.mode.value,
        "company_configured": settings.get("paye_reference_configured") and settings.get("accounts_office_reference_configured"),
        "settings": settings,
        "disclaimers": {
            "hmrc_alignment": "This software is RTI-compatible. HMRC does not endorse or certify payroll software.",
            "employer_responsibility": "Compliance with RTI regulations is the employer's legal responsibility.",
            "submission_approval": "All HMRC submissions require explicit human approval."
        }
    }


@router.get("/submissions")
async def list_submissions(
    state: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(require_payroll_admin)
):
    """
    List RTI submissions for the company.
    
    Filter by state: preparing, queued, approval_pending, approved, submitted, accepted, etc.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    query = {"company_id": user.company_id}
    if state:
        query["state"] = state
    
    submissions = await db.rti_submissions.find(
        query,
        {"_id": 0, "xml_content": 0}  # Exclude payload
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "submissions": submissions,
        "total": len(submissions)
    }


@router.get("/submissions/{submission_id}")
async def get_submission_detail(
    submission_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Get detailed submission information including audit trail.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    from services.rti_sync_service import get_submission_summary
    
    summary = await get_submission_summary(submission_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Verify company access
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id},
        {"_id": 0}
    )
    if submission.get("company_id") != user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return summary


# ==================== PREPARATION ROUTES ====================

@router.post("/prepare")
async def prepare_submission(
    request_data: PrepareSubmissionRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Prepare FPS submission for a pay run.
    
    This will:
    1. Validate the pay run exists and is approved
    2. Generate FPS XML payload
    3. Run validation against HMRC specifications
    4. Queue for approval if valid
    
    Does NOT submit to HMRC - requires explicit approval.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Verify pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": request_data.payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    if payrun.get("status") not in ["approved", "paid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pay run must be approved before RTI preparation. Current status: {payrun.get('status')}"
        )
    
    from services.rti_sync_service import rti_sync_engine
    
    try:
        result = await rti_sync_engine.prepare_fps(
            payrun_id=request_data.payrun_id,
            company_id=user.company_id,
            initiated_by=user.user_id
        )
        
        return {
            "status": result.get("status"),
            "submission_id": result.get("submission_id"),
            "validation": result.get("validation"),
            "next_step": "Request approval to proceed with submission" if result.get("validation", {}).get("valid") else "Fix blocking issues before proceeding"
        }
        
    except Exception as e:
        logger.error(f"FPS preparation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submissions/{submission_id}/validate")
async def revalidate_submission(
    submission_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Re-run validation on a submission.
    
    Useful after fixing employee data issues.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from services.rti_sync_service import rti_sync_engine
    
    result = await rti_sync_engine.validate_submission(submission_id)
    
    return {
        "submission_id": submission_id,
        "validation": result
    }


# ==================== APPROVAL WORKFLOW ROUTES ====================

@router.post("/submissions/{submission_id}/request-approval")
async def request_approval(
    submission_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Request approval for an RTI submission.
    
    Moves submission to approval queue for review by Owner or Payroll Admin.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from services.rti_sync_service import rti_sync_engine
    
    try:
        result = await rti_sync_engine.request_approval(submission_id, user.user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: str,
    approval: ApprovalRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Approve an RTI submission for HMRC.
    
    REQUIREMENTS:
    - User must be Owner or Payroll Admin
    - Confirmation text must match exactly: "I confirm submission {submission_id}"
    - This creates an immutable audit record
    
    After approval, the submission can be sent to HMRC.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from services.rti_sync_service import rti_sync_engine
    
    try:
        result = await rti_sync_engine.approve_submission(
            submission_id=submission_id,
            approved_by=user.user_id,
            approver_role=user.role,
            confirmation_text=approval.confirmation_text
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    rejection: RejectionRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Reject an RTI submission.
    
    The submission will be cancelled and a new one must be prepared.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from services.rti_sync_service import rti_sync_engine
    
    try:
        result = await rti_sync_engine.reject_submission(
            submission_id=submission_id,
            rejected_by=user.user_id,
            rejection_reason=rejection.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== SUBMISSION ROUTES ====================

@router.post("/submissions/{submission_id}/submit")
async def submit_to_hmrc(
    submission_id: str,
    submit_request: SubmitRequest,
    user: User = Depends(require_payroll_admin)
):
    """
    Submit approved FPS/EPS to HMRC.
    
    IMPORTANT:
    - Submission must be in APPROVED state
    - User must acknowledge disclaimer
    - Creates immutable receipt record
    - In Sandbox mode: submits to HMRC test environment
    - In Live mode: submits to production (requires feature flag)
    
    DISCLAIMER:
    This software is HMRC RTI-compatible but is not endorsed or certified by HMRC.
    Compliance with RTI regulations is the employer's legal responsibility.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    if not submit_request.acknowledge_disclaimer:
        raise HTTPException(
            status_code=400,
            detail="You must acknowledge the HMRC compliance disclaimer before submitting"
        )
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    from services.rti_sync_service import rti_sync_engine
    
    try:
        result = await rti_sync_engine.submit_to_hmrc(submission_id, user.user_id)
        
        # Update pay run RTI status
        if result.get("status") == "submitted" and submission.get("payrun_id"):
            await db.pay_runs.update_one(
                {"payrun_id": submission["payrun_id"]},
                {"$set": {
                    "rti_submitted": True,
                    "rti_submission_id": submission_id,
                    "rti_correlation_id": result.get("correlation_id")
                }}
            )
        
        return {
            **result,
            "disclaimer": "This submission was made to HMRC in compliance with RTI regulations. Retain the correlation ID for your records."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"HMRC submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIT ROUTES ====================

@router.get("/submissions/{submission_id}/audit-trail")
async def get_audit_trail(
    submission_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Get immutable audit trail for a submission.
    
    Includes all actions: preparation, validation, approval, submission, receipts.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Get audit entries
    audit_entries = await db.rti_audit_ledger.find(
        {"submission_id": submission_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(1000)
    
    # Get receipts
    receipts = await db.rti_receipts.find(
        {"submission_id": submission_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    
    return {
        "submission_id": submission_id,
        "audit_entries": audit_entries,
        "receipts": receipts,
        "entry_count": len(audit_entries),
        "integrity_note": "Entries with 'immutable: true' include cryptographic hashes for verification"
    }


@router.get("/receipts")
async def list_receipts(
    limit: int = 50,
    user: User = Depends(require_payroll_admin)
):
    """
    List HMRC submission receipts.
    
    Receipts are immutable records of submissions to HMRC.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    receipts = await db.rti_receipts.find(
        {"company_id": user.company_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "receipts": receipts,
        "total": len(receipts)
    }


# ==================== HEALTH CHECK ROUTE ====================

@router.get("/health-check/{payrun_id}")
async def rti_health_check(
    payrun_id: str,
    user: User = Depends(require_payroll_admin)
):
    """
    Run RTI health check on a pay run before preparation.
    
    Returns blocking issues that must be fixed before FPS submission.
    This uses the same validation logic as the RTI Sync Engine.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    payrun = await db.pay_runs.find_one(
        {"payrun_id": payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Run validation
    from services.rti_sync_service import rti_sync_engine
    
    issues = []
    issues.extend(rti_sync_engine._validate_company_hmrc_data(company))
    for emp in employees:
        issues.extend(rti_sync_engine._validate_employee_rti_data(emp))
    issues.extend(rti_sync_engine._validate_payrun_data(payrun, payslips))
    
    blocking_issues = [i for i in issues if i.is_blocking()]
    warnings = [i for i in issues if not i.is_blocking()]
    
    return {
        "payrun_id": payrun_id,
        "ready_for_rti": len(blocking_issues) == 0,
        "score": max(0, 100 - (len(blocking_issues) * 15) - (len(warnings) * 5)),
        "blocking_issues": [i.to_dict() for i in blocking_issues],
        "warnings": [i.to_dict() for i in warnings],
        "employee_count": len(payslips),
        "total_pay": sum(ps.get("gross_pay", 0) for ps in payslips),
        "recommendation": (
            "Ready for FPS preparation" if len(blocking_issues) == 0 
            else f"Fix {len(blocking_issues)} blocking issue(s) before proceeding"
        )
    }
