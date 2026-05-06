"""
RealtouchHR - Email Service
Mock implementation with easy Resend API key replacement
"""
import os
import logging
from typing import Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ==================== EMAIL CONFIGURATION ====================

# Replace with your Resend API key - set in .env file
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@realtouchhr.com')
COMPANY_NAME = "RealtouchHR"

# Email templates base URL (for links in emails)
APP_URL = os.environ.get('APP_URL', 'https://realtouchhr.com')


class EmailService:
    """
    Email service with mock implementation.
    Replace RESEND_API_KEY in .env to enable real emails.
    """
    
    def __init__(self):
        self.api_key = RESEND_API_KEY
        self.sender = SENDER_EMAIL
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                import resend
                resend.api_key = self.api_key
                self.resend = resend
                logger.info("Email service initialized with Resend API")
            except ImportError:
                logger.warning("Resend library not installed. Using mock emails.")
                self.enabled = False
        else:
            logger.info("Email service running in MOCK mode. Set RESEND_API_KEY to enable.")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> dict:
        """
        Send an email. Returns success status and message ID or mock ID.
        """
        if self.enabled:
            try:
                params = {
                    "from": f"{COMPANY_NAME} <{self.sender}>",
                    "to": [to],
                    "subject": subject,
                    "html": html_content,
                }
                if text_content:
                    params["text"] = text_content
                
                response = self.resend.Emails.send(params)
                logger.info(f"Email sent to {to}: {response.get('id')}")
                return {"success": True, "message_id": response.get("id"), "mock": False}
            except Exception as e:
                logger.error(f"Failed to send email to {to}: {e}")
                return {"success": False, "error": str(e), "mock": False}
        else:
            # Mock implementation - log the email
            mock_id = f"mock_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{to.split('@')[0]}"
            logger.info(f"[MOCK EMAIL] To: {to}, Subject: {subject}, ID: {mock_id}")
            return {"success": True, "message_id": mock_id, "mock": True}
    
    async def send_bulk_emails(
        self,
        recipients: List[str],
        subject: str,
        html_content: str
    ) -> dict:
        """Send the same email to multiple recipients"""
        results = {"sent": 0, "failed": 0, "mock": not self.enabled}
        
        for to in recipients:
            result = await self.send_email(to, subject, html_content)
            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        return results

    # ==================== Convenience helpers ====================

    async def send_visa_expiry_alert(self, to: str, employee_name: str, visa_type: str,
                                     expiry_date: str, days_until: int,
                                     manager_name: Optional[str] = None) -> dict:
        subject = f"Visa expiring in {days_until} days - {employee_name}"
        html = visa_expiry_alert_email(employee_name, visa_type, expiry_date, days_until, manager_name)
        return await self.send_email(to, subject, html)

    async def send_timesheet_approval(self, to: str, employee_name: str, week_start: str,
                                      hours_worked: float, status: str,
                                      approver_name: Optional[str] = None,
                                      rejection_reason: Optional[str] = None) -> dict:
        subject = f"Timesheet {status} - Week of {week_start}"
        html = timesheet_approval_email(employee_name, week_start, hours_worked, status,
                                        approver_name, rejection_reason)
        return await self.send_email(to, subject, html)

    async def send_pension_enrolment(self, to: str, employee_name: str, scheme_name: str,
                                     enrolment_date: str, employee_contribution_pct: float,
                                     employer_contribution_pct: float,
                                     opt_out_window_end: str) -> dict:
        subject = "Workplace Pension - Auto-Enrolment Confirmation"
        html = pension_enrolment_email(employee_name, scheme_name, enrolment_date,
                                       employee_contribution_pct, employer_contribution_pct,
                                       opt_out_window_end)
        return await self.send_email(to, subject, html)

    async def send_subscription_confirmation(self, to_email: str, plan_name: str,
                                             amount: float, currency: str = "gbp",
                                             user_name: str = "there") -> dict:
        subject = f"Subscription Confirmed - {plan_name}"
        html = subscription_confirmation_email(user_name, plan_name, amount, currency)
        return await self.send_email(to_email, subject, html)


# ==================== EMAIL TEMPLATES ====================

def get_base_template(content: str, footer_text: str = "") -> str:
    """Base HTML email template with RealtouchHR branding"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RealtouchHR</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f5;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f5; padding: 20px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">RealtouchHR</h1>
                                <p style="color: #e0e7ff; margin: 8px 0 0 0; font-size: 14px;">Compliance Confidence for UK Businesses</p>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                {content}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f9fafb; padding: 20px 30px; border-top: 1px solid #e5e7eb;">
                                <p style="color: #6b7280; font-size: 12px; margin: 0; text-align: center;">
                                    {footer_text if footer_text else f"© {datetime.now().year} RealtouchHR. All rights reserved."}
                                </p>
                                <p style="color: #9ca3af; font-size: 11px; margin: 8px 0 0 0; text-align: center;">
                                    This is an automated message. Please do not reply directly to this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def leave_approval_email(
    employee_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    days: int,
    status: str,
    approver_name: Optional[str] = None
) -> str:
    """Generate leave approval/rejection email content"""
    is_approved = status.lower() == "approved"
    status_color = "#10b981" if is_approved else "#ef4444"
    status_icon = "✓" if is_approved else "✗"
    
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Leave Request {status.title()}
        </h2>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {employee_name},
        </p>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Your <strong>{leave_type}</strong> leave request has been 
            <span style="color: {status_color}; font-weight: 600;">{status_icon} {status.lower()}</span>.
        </p>
        
        <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 0 0 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: #6b7280; font-size: 14px;">Leave Type:</span>
                        <span style="color: #111827; font-size: 14px; font-weight: 600; float: right;">{leave_type}</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb;">
                        <span style="color: #6b7280; font-size: 14px;">From:</span>
                        <span style="color: #111827; font-size: 14px; font-weight: 600; float: right;">{start_date}</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb;">
                        <span style="color: #6b7280; font-size: 14px;">To:</span>
                        <span style="color: #111827; font-size: 14px; font-weight: 600; float: right;">{end_date}</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb;">
                        <span style="color: #6b7280; font-size: 14px;">Total Days:</span>
                        <span style="color: #111827; font-size: 14px; font-weight: 600; float: right;">{days}</span>
                    </td>
                </tr>
                {f'''<tr>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb;">
                        <span style="color: #6b7280; font-size: 14px;">{"Approved" if is_approved else "Reviewed"} by:</span>
                        <span style="color: #111827; font-size: 14px; font-weight: 600; float: right;">{approver_name}</span>
                    </td>
                </tr>''' if approver_name else ''}
            </table>
        </div>
        
        <p style="color: #374151; font-size: 14px; line-height: 1.6; margin: 0;">
            {"Enjoy your time off!" if is_approved else "If you have any questions, please contact your manager or HR."}
        </p>
    """
    return get_base_template(content)


def payslip_available_email(
    employee_name: str,
    pay_period: str,
    pay_date: str,
    net_pay: float
) -> str:
    """Generate payslip availability notification email"""
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Your Payslip is Ready 💰
        </h2>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {employee_name},
        </p>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Your payslip for <strong>{pay_period}</strong> is now available.
        </p>
        
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border-radius: 8px; padding: 24px; margin: 0 0 24px 0; text-align: center;">
            <p style="color: #e0e7ff; font-size: 14px; margin: 0 0 8px 0;">Net Pay</p>
            <p style="color: #ffffff; font-size: 36px; font-weight: 700; margin: 0;">£{net_pay:,.2f}</p>
            <p style="color: #c7d2fe; font-size: 14px; margin: 8px 0 0 0;">Payment Date: {pay_date}</p>
        </div>
        
        <div style="text-align: center; margin: 0 0 24px 0;">
            <a href="{APP_URL}/self-service/payslips" 
               style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                View Payslip
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
            You can also download a PDF copy from your self-service portal.
        </p>
    """
    return get_base_template(content)


def compliance_reminder_email(
    user_name: str,
    tasks: list,
    company_compliance_score: int
) -> str:
    """Generate compliance reminder email"""
    task_items = ""
    for task in tasks[:5]:  # Limit to 5 tasks
        priority_color = "#ef4444" if task.get("priority") == "high" else "#f59e0b" if task.get("priority") == "medium" else "#6b7280"
        task_items += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                    <span style="display: inline-block; width: 8px; height: 8px; background-color: {priority_color}; border-radius: 50%; margin-right: 8px;"></span>
                    <span style="color: #111827; font-size: 14px;">{task.get('title', 'Task')}</span>
                </td>
            </tr>
        """
    
    score_color = "#10b981" if company_compliance_score >= 90 else "#f59e0b" if company_compliance_score >= 70 else "#ef4444"
    
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Compliance Update Required
        </h2>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {user_name},
        </p>
        
        <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 0 0 24px 0; text-align: center;">
            <p style="color: #6b7280; font-size: 14px; margin: 0 0 8px 0;">Current Compliance Score</p>
            <p style="color: {score_color}; font-size: 48px; font-weight: 700; margin: 0;">{company_compliance_score}%</p>
        </div>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
            You have <strong>{len(tasks)}</strong> pending compliance task(s):
        </p>
        
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 8px; margin: 0 0 24px 0;">
            {task_items}
        </table>
        
        <div style="text-align: center;">
            <a href="{APP_URL}/settings" 
               style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Review Tasks
            </a>
        </div>
    """
    return get_base_template(content)


def welcome_email(user_name: str, company_name: str) -> str:
    """Generate welcome email for new users"""
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Welcome to RealtouchHR! 🎉
        </h2>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {user_name},
        </p>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Thank you for creating your <strong>{company_name}</strong> account on RealtouchHR. 
            You're now ready to streamline your HR and payroll operations with compliance confidence.
        </p>
        
        <h3 style="color: #111827; margin: 0 0 16px 0; font-size: 18px;">Get Started:</h3>
        
        <div style="margin: 0 0 24px 0;">
            <div style="display: flex; align-items: flex-start; margin: 0 0 16px 0;">
                <span style="display: inline-block; background-color: #4f46e5; color: #ffffff; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-size: 12px; font-weight: 600; margin-right: 12px;">1</span>
                <span style="color: #374151; font-size: 14px;">Add your first employee</span>
            </div>
            <div style="display: flex; align-items: flex-start; margin: 0 0 16px 0;">
                <span style="display: inline-block; background-color: #4f46e5; color: #ffffff; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-size: 12px; font-weight: 600; margin-right: 12px;">2</span>
                <span style="color: #374151; font-size: 14px;">Complete company setup</span>
            </div>
            <div style="display: flex; align-items: flex-start; margin: 0 0 16px 0;">
                <span style="display: inline-block; background-color: #4f46e5; color: #ffffff; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-size: 12px; font-weight: 600; margin-right: 12px;">3</span>
                <span style="color: #374151; font-size: 14px;">Run your first payroll preview</span>
            </div>
        </div>
        
        <div style="text-align: center; margin: 0 0 24px 0;">
            <a href="{APP_URL}/onboarding" 
               style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Start Onboarding
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
            Need help? Our AI Copilot is available 24/7 to guide you through any process.
        </p>
    """
    return get_base_template(content)


def visa_expiry_alert_email(
    employee_name: str,
    visa_type: str,
    expiry_date: str,
    days_until: int,
    manager_name: Optional[str] = None
) -> str:
    """Visa expiry alert email for UKVI-sponsored employees or HR managers"""
    urgency_color = "#ef4444" if days_until <= 7 else "#f59e0b" if days_until <= 30 else "#3b82f6"
    urgency_label = "URGENT" if days_until <= 7 else "ACTION REQUIRED" if days_until <= 30 else "REMINDER"
    content = f"""
        <div style="display: inline-block; padding: 4px 12px; background-color: {urgency_color}; color: #fff; border-radius: 999px; font-size: 12px; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 16px;">
            {urgency_label}
        </div>
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Visa Expiry Approaching
        </h2>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            Hi {manager_name or 'HR Team'},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            <strong>{employee_name}'s</strong> <strong>{visa_type}</strong> visa is due to expire in
            <strong style="color: {urgency_color};">{days_until} days</strong> (on {expiry_date}).
        </p>
        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 6px; margin: 0 0 24px 0;">
            <p style="color: #92400e; font-size: 14px; margin: 0; line-height: 1.5;">
                <strong>Home Office reporting obligations:</strong> Sponsored workers must be reported
                if their employment ends. Ensure extension is in progress or plan next steps.
            </p>
        </div>
        <div style="text-align: center; margin: 0 0 24px 0;">
            <a href="{APP_URL}/ukvi" style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Open UKVI Compliance
            </a>
        </div>
    """
    return get_base_template(content)


def timesheet_approval_email(
    employee_name: str,
    week_start: str,
    hours_worked: float,
    status: str,
    approver_name: Optional[str] = None,
    rejection_reason: Optional[str] = None
) -> str:
    """Timesheet approved/rejected notification"""
    is_approved = status.lower() == "approved"
    status_color = "#10b981" if is_approved else "#ef4444"
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Timesheet {status.title()}
        </h2>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            Hi {employee_name},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Your timesheet for the week starting <strong>{week_start}</strong> has been
            <span style="color: {status_color}; font-weight: 700;">{status.lower()}</span>{f' by {approver_name}' if approver_name else ''}.
        </p>
        <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 0 0 24px 0;">
            <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Hours worked</p>
            <p style="margin: 0; color: #111827; font-size: 28px; font-weight: 700;">{hours_worked:.2f} hrs</p>
        </div>
        {f'''<div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 16px; border-radius: 6px; margin: 0 0 24px 0;">
            <p style="color: #991b1b; font-size: 14px; margin: 0 0 4px 0; font-weight: 700;">Reason for rejection</p>
            <p style="color: #991b1b; font-size: 14px; margin: 0; line-height: 1.5;">{rejection_reason}</p>
        </div>''' if rejection_reason else ''}
        <div style="text-align: center;">
            <a href="{APP_URL}/time-tracking" style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                View Timesheet
            </a>
        </div>
    """
    return get_base_template(content)


def pension_enrolment_email(
    employee_name: str,
    scheme_name: str,
    enrolment_date: str,
    employee_contribution_pct: float,
    employer_contribution_pct: float,
    opt_out_window_end: str
) -> str:
    """Statutory pension auto-enrolment confirmation email"""
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            You've Been Auto-Enrolled in a Workplace Pension
        </h2>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            Hi {employee_name},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Under the Pensions Act 2008, your employer is required to automatically enrol eligible
            workers into a workplace pension. We're pleased to confirm your enrolment.
        </p>
        <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 0 0 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Scheme:</td>
                    <td style="padding: 8px 0; color: #111827; font-size: 14px; font-weight: 600; text-align: right;">{scheme_name}</td></tr>
                <tr><td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Enrolment Date:</td>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #111827; font-size: 14px; font-weight: 600; text-align: right;">{enrolment_date}</td></tr>
                <tr><td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Your contribution:</td>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #111827; font-size: 14px; font-weight: 600; text-align: right;">{employee_contribution_pct}% of qualifying earnings</td></tr>
                <tr><td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">Employer contribution:</td>
                    <td style="padding: 8px 0; border-top: 1px solid #e5e7eb; color: #111827; font-size: 14px; font-weight: 600; text-align: right;">{employer_contribution_pct}%</td></tr>
            </table>
        </div>
        <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 6px; margin: 0 0 24px 0;">
            <p style="color: #92400e; font-size: 14px; margin: 0 0 4px 0; font-weight: 700;">Opt-out window</p>
            <p style="color: #92400e; font-size: 14px; margin: 0; line-height: 1.5;">
                You have 1 month to opt out with a full refund (until <strong>{opt_out_window_end}</strong>).
                After this, contributions can still be stopped but won't be refunded.
            </p>
        </div>
        <div style="text-align: center;">
            <a href="{APP_URL}/self-service" style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Manage Pension
            </a>
        </div>
    """
    return get_base_template(content)


def subscription_confirmation_email(
    user_name: str,
    plan_name: str,
    amount: float,
    currency: str = "gbp"
) -> str:
    """Subscription payment confirmation"""
    currency_symbol = "£" if currency.lower() == "gbp" else "$" if currency.lower() == "usd" else currency.upper() + " "
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            Subscription Confirmed
        </h2>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
            Hi {user_name},
        </p>
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Your <strong>{plan_name}</strong> plan is now active. Thank you for choosing RealtouchHR.
        </p>
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border-radius: 8px; padding: 24px; margin: 0 0 24px 0; text-align: center;">
            <p style="color: #e0e7ff; font-size: 14px; margin: 0 0 8px 0;">Amount charged</p>
            <p style="color: #ffffff; font-size: 36px; font-weight: 700; margin: 0;">{currency_symbol}{amount:,.2f}</p>
            <p style="color: #c7d2fe; font-size: 14px; margin: 8px 0 0 0;">{plan_name}</p>
        </div>
        <div style="text-align: center;">
            <a href="{APP_URL}/billing" style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                View Billing
            </a>
        </div>
    """
    return get_base_template(content)


def employee_invite_email(
    employee_name: str,
    company_name: str,
    invite_link: str
) -> str:
    """Generate employee self-service invite email"""
    content = f"""
        <h2 style="color: #111827; margin: 0 0 20px 0; font-size: 22px;">
            You're Invited to RealtouchHR
        </h2>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {employee_name},
        </p>
        
        <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
            <strong>{company_name}</strong> has invited you to access your employee self-service portal on RealtouchHR.
        </p>
        
        <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 0 0 24px 0;">
            <h3 style="color: #111827; margin: 0 0 12px 0; font-size: 16px;">With self-service, you can:</h3>
            <ul style="color: #374151; font-size: 14px; margin: 0; padding-left: 20px;">
                <li style="margin: 8px 0;">View and download your payslips</li>
                <li style="margin: 8px 0;">Request time off</li>
                <li style="margin: 8px 0;">Check your leave balance</li>
                <li style="margin: 8px 0;">Update your personal details</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 0 0 24px 0;">
            <a href="{invite_link}" 
               style="display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Set Up My Account
            </a>
        </div>
        
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
            This invitation link will expire in 7 days. If you didn't expect this email, please ignore it.
        </p>
    """
    return get_base_template(content)


# Singleton instance
email_service = EmailService()
