"""
RealtouchHR - HMRC RTI Routes
Full Payment Submission (FPS) and Employer Payment Summary (EPS)
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
import logging

from models import (
    User, RTISubmission, RTISubmissionRequest, PayrollHealthCheckResult, 
    HealthCheckIssue, EPSData
)
from utils import db, generate_submission_id, now_utc, now_iso
from routes.auth import get_current_user, require_payroll
from services.hmrc_service import hmrc_service, RTIValidator, RTIStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hmrc", tags=["HMRC RTI"])


# ==================== VALIDATION ====================

@router.post("/validate/{payrun_id}")
async def validate_payrun_for_rti(
    payrun_id: str,
    user: User = Depends(require_payroll)
):
    """
    Validate a pay run for HMRC RTI submission.
    Returns validation errors and warnings.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Validate
    result = await hmrc_service.validate_fps(company, payrun, employees, payslips)
    
    return result


@router.get("/health-check/{payrun_id}", response_model=PayrollHealthCheckResult)
async def payroll_health_check(
    payrun_id: str,
    user: User = Depends(require_payroll)
):
    """
    Comprehensive health check before RTI submission.
    Checks data quality, anomalies, and compliance issues.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    issues = []
    score = 100
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Check each employee
    for emp in employees:
        emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
        
        # Missing NI number
        if not emp.get("ni_number"):
            issues.append(HealthCheckIssue(
                severity="critical",
                category="missing_data",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing NI Number",
                description=f"{emp_name} does not have a National Insurance number",
                action_required="Add NI number to employee record"
            ))
            score -= 10
        
        # Invalid NI format
        elif not RTIValidator.validate_ni_number(emp.get("ni_number")) is None:
            issues.append(HealthCheckIssue(
                severity="critical",
                category="compliance",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Invalid NI Number Format",
                description=f"{emp_name} has an invalid NI number format",
                action_required="Correct the NI number format"
            ))
            score -= 10
        
        # Missing tax code
        if not emp.get("tax_code"):
            issues.append(HealthCheckIssue(
                severity="warning",
                category="missing_data",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing Tax Code",
                description=f"{emp_name} does not have a tax code - defaulting to 1257L",
                action_required="Add correct tax code"
            ))
            score -= 5
        
        # Missing bank details
        if not emp.get("bank_account") or not emp.get("bank_sort_code"):
            issues.append(HealthCheckIssue(
                severity="warning",
                category="banking",
                employee_id=emp.get("employee_id"),
                employee_name=emp_name,
                title="Missing Bank Details",
                description=f"{emp_name} has incomplete banking information",
                action_required="Add bank account and sort code"
            ))
            score -= 5
    
    # Check company HMRC details
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    if not company.get("paye_reference"):
        issues.append(HealthCheckIssue(
            severity="critical",
            category="compliance",
            employee_id=None,
            employee_name=None,
            title="Missing PAYE Reference",
            description="Company PAYE reference is required for HMRC submission",
            action_required="Add PAYE reference in company settings"
        ))
        score -= 20
    
    if not company.get("accounts_office_reference"):
        issues.append(HealthCheckIssue(
            severity="critical",
            category="compliance",
            employee_id=None,
            employee_name=None,
            title="Missing Accounts Office Reference",
            description="Accounts Office Reference is required for HMRC submission",
            action_required="Add Accounts Office Reference in company settings"
        ))
        score -= 20
    
    # Check for anomalies
    for ps in payslips:
        emp = next((e for e in employees if e.get("employee_id") == ps.get("employee_id")), None)
        if emp:
            emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}"
            
            # Check for unusually high/low pay
            expected_monthly = (emp.get("salary", 0) or 0) / 12
            actual_gross = ps.get("gross_pay", 0)
            
            if expected_monthly > 0:
                variance = abs(actual_gross - expected_monthly) / expected_monthly
                if variance > 0.5:  # More than 50% variance
                    issues.append(HealthCheckIssue(
                        severity="warning",
                        category="anomaly",
                        employee_id=emp.get("employee_id"),
                        employee_name=emp_name,
                        title="Pay Variance Detected",
                        description=f"{emp_name}'s gross pay (£{actual_gross:.2f}) varies significantly from expected (£{expected_monthly:.2f})",
                        action_required="Verify pay calculations are correct"
                    ))
                    score -= 3
    
    score = max(0, score)
    
    # Determine overall status
    critical_count = len([i for i in issues if i.severity == "critical"])
    warning_count = len([i for i in issues if i.severity == "warning"])
    
    if critical_count > 0:
        overall_status = "fail"
        can_proceed = False
    elif warning_count > 3:
        overall_status = "warning"
        can_proceed = True
    elif warning_count > 0:
        overall_status = "warning"
        can_proceed = True
    else:
        overall_status = "pass"
        can_proceed = True
    
    return PayrollHealthCheckResult(
        payrun_id=payrun_id,
        check_date=now_iso()[:10],
        overall_status=overall_status,
        score=score,
        issues=issues,
        can_proceed=can_proceed
    )


# ==================== FPS SUBMISSION ====================

@router.post("/fps/submit")
async def submit_fps(
    request: RTISubmissionRequest,
    user: User = Depends(require_payroll)
):
    """
    Submit Full Payment Submission (FPS) to HMRC.
    
    The FPS reports pay and deductions for all employees paid in this pay period.
    Must be submitted on or before each payday.
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get pay run
    payrun = await db.pay_runs.find_one(
        {"payrun_id": request.payrun_id, "company_id": user.company_id},
        {"_id": 0}
    )
    if not payrun:
        raise HTTPException(status_code=404, detail="Pay run not found")
    
    # Check if already submitted
    if payrun.get("rti_submitted"):
        raise HTTPException(
            status_code=400,
            detail="This pay run has already been submitted to HMRC"
        )
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    # Get employees and payslips
    employees = await db.employees.find(
        {"company_id": user.company_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    payslips = await db.payslips.find(
        {"payrun_id": request.payrun_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Validate before submission
    validation = await hmrc_service.validate_fps(company, payrun, employees, payslips)
    if not validation["valid"]:
        return {
            "success": False,
            "status": "validation_failed",
            "errors": validation["errors"],
            "warnings": validation["warnings"]
        }
    
    # Create submission record
    submission_id = generate_submission_id()
    now = now_utc()
    
    submission_doc = {
        "submission_id": submission_id,
        "company_id": user.company_id,
        "payrun_id": request.payrun_id,
        "submission_type": "FPS",
        "status": RTIStatus.VALIDATING.value,
        "validation_errors": [],
        "validation_warnings": validation.get("warnings", []),
        "test_mode": request.test_mode,
        "created_by": user.user_id,
        "created_at": now.isoformat()
    }
    await db.rti_submissions.insert_one(submission_doc)
    
    # Generate XML
    credentials = {
        "sender_id": company.get("hmrc_sender_id", ""),
        "password": company.get("hmrc_password", "")
    }
    
    try:
        xml_content = await hmrc_service.generate_fps_xml(
            company, payrun, employees, payslips, credentials
        )
        
        # Store XML for reference
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"xml_content": xml_content, "status": RTIStatus.VALIDATED.value}}
        )
        
        # Submit to HMRC (test mode)
        if request.test_mode:
            result = await hmrc_service.submit_to_hmrc(xml_content, "FPS")
            
            if result["success"]:
                await db.rti_submissions.update_one(
                    {"submission_id": submission_id},
                    {
                        "$set": {
                            "status": RTIStatus.SUBMITTED.value,
                            "correlation_id": result.get("correlation_id"),
                            "poll_url": result.get("poll_url"),
                            "hmrc_response": result,
                            "submitted_at": now.isoformat()
                        }
                    }
                )
                
                # Mark pay run as submitted
                await db.pay_runs.update_one(
                    {"payrun_id": request.payrun_id},
                    {
                        "$set": {
                            "rti_submitted": True,
                            "rti_submission_id": submission_id,
                            "status": "submitted"
                        }
                    }
                )
                
                return {
                    "success": True,
                    "submission_id": submission_id,
                    "status": "submitted",
                    "correlation_id": result.get("correlation_id"),
                    "message": result.get("message"),
                    "test_mode": request.test_mode
                }
            else:
                await db.rti_submissions.update_one(
                    {"submission_id": submission_id},
                    {"$set": {"status": RTIStatus.ERROR.value, "hmrc_response": result}}
                )
                return {
                    "success": False,
                    "submission_id": submission_id,
                    "status": "error",
                    "error": result.get("error")
                }
        else:
            # Production submission requires additional setup
            return {
                "success": False,
                "submission_id": submission_id,
                "status": "pending",
                "message": "Production submissions require HMRC Gateway credentials. Please configure in settings."
            }
            
    except Exception as e:
        logger.error(f"FPS submission error: {e}")
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"status": RTIStatus.ERROR.value, "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EPS SUBMISSION ====================

@router.post("/eps/submit")
async def submit_eps(
    eps_data: EPSData,
    user: User = Depends(require_payroll)
):
    """
    Submit Employer Payment Summary (EPS) to HMRC.
    
    Use EPS to report:
    - Recoverable amounts (SMP, SPP, SAP, etc.)
    - No employees paid in a tax month
    - Final submission for the tax year
    """
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    # Get company
    company = await db.companies.find_one(
        {"company_id": user.company_id},
        {"_id": 0}
    )
    
    if not company.get("paye_reference"):
        raise HTTPException(
            status_code=400,
            detail="PAYE reference is required for EPS submission"
        )
    
    # Create submission record
    submission_id = generate_submission_id()
    now = now_utc()
    
    # Determine tax month and year
    tax_month = hmrc_service.get_tax_month(now.isoformat()[:10])
    tax_year = hmrc_service.get_tax_year(now.isoformat()[:10])
    
    submission_doc = {
        "submission_id": submission_id,
        "company_id": user.company_id,
        "payrun_id": None,
        "submission_type": "EPS",
        "status": RTIStatus.VALIDATING.value,
        "tax_month": tax_month,
        "tax_year": tax_year,
        "eps_data": eps_data.dict(),
        "created_by": user.user_id,
        "created_at": now.isoformat()
    }
    await db.rti_submissions.insert_one(submission_doc)
    
    # Generate XML
    credentials = {
        "sender_id": company.get("hmrc_sender_id", ""),
        "password": company.get("hmrc_password", "")
    }
    
    try:
        xml_content = await hmrc_service.generate_eps_xml(
            company, tax_month, tax_year, eps_data.dict(), credentials
        )
        
        await db.rti_submissions.update_one(
            {"submission_id": submission_id},
            {"$set": {"xml_content": xml_content, "status": RTIStatus.VALIDATED.value}}
        )
        
        # Submit (test mode only for now)
        result = await hmrc_service.submit_to_hmrc(xml_content, "EPS")
        
        if result["success"]:
            await db.rti_submissions.update_one(
                {"submission_id": submission_id},
                {
                    "$set": {
                        "status": RTIStatus.SUBMITTED.value,
                        "correlation_id": result.get("correlation_id"),
                        "hmrc_response": result,
                        "submitted_at": now.isoformat()
                    }
                }
            )
            
            return {
                "success": True,
                "submission_id": submission_id,
                "status": "submitted",
                "tax_month": tax_month,
                "tax_year": tax_year,
                "message": result.get("message")
            }
        else:
            return {
                "success": False,
                "submission_id": submission_id,
                "error": result.get("error")
            }
            
    except Exception as e:
        logger.error(f"EPS submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SUBMISSION STATUS ====================

@router.get("/submissions", response_model=List[RTISubmission])
async def get_rti_submissions(
    limit: int = 50,
    user: User = Depends(require_payroll)
):
    """Get RTI submission history"""
    if not user.company_id:
        return []
    
    submissions = await db.rti_submissions.find(
        {"company_id": user.company_id},
        {"_id": 0, "xml_content": 0}  # Exclude large XML
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for sub in submissions:
        if isinstance(sub.get("created_at"), str):
            sub["created_at"] = datetime.fromisoformat(sub["created_at"])
        if isinstance(sub.get("submitted_at"), str):
            sub["submitted_at"] = datetime.fromisoformat(sub["submitted_at"])
    
    return [RTISubmission(**sub) for sub in submissions]


@router.get("/submissions/{submission_id}")
async def get_rti_submission(
    submission_id: str,
    user: User = Depends(require_payroll)
):
    """Get RTI submission details"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission


@router.post("/submissions/{submission_id}/poll")
async def poll_submission_status(
    submission_id: str,
    user: User = Depends(require_payroll)
):
    """Poll HMRC for submission status update"""
    if not user.company_id:
        raise HTTPException(status_code=400, detail="No company setup")
    
    submission = await db.rti_submissions.find_one(
        {"submission_id": submission_id, "company_id": user.company_id},
        {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    poll_url = submission.get("poll_url")
    if not poll_url:
        return {"status": submission.get("status"), "message": "No poll URL available"}
    
    # Poll HMRC
    result = await hmrc_service.poll_submission_status(poll_url)
    
    # Update status
    new_status = RTIStatus.ACCEPTED.value if result.get("status") == "accepted" else submission.get("status")
    
    await db.rti_submissions.update_one(
        {"submission_id": submission_id},
        {
            "$set": {
                "status": new_status,
                "poll_response": result,
                "accepted_at": datetime.now(timezone.utc).isoformat() if new_status == RTIStatus.ACCEPTED.value else None
            }
        }
    )
    
    return {
        "submission_id": submission_id,
        "status": new_status,
        "hmrc_response": result
    }
