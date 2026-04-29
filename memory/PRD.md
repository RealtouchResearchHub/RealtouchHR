# RealtouchHR - Product Requirements Document

## Overview
RealtouchHR is a next-generation HR, Payroll, and Compliance SaaS platform designed for the UK market with global extensibility.

---

## Implemented Features (April 29, 2026)

### Core HR Module ✅
- [x] Employee records management (CRUD)
- [x] Employee detail views with compliance scoring
- [x] Bulk employee import (CSV)
- [x] Leave management and approval workflows
- [x] Document management and storage

### Authentication ✅
- [x] JWT-based authentication (email/password)
- [x] Emergent-managed Google Social Login
- [x] Role-based access control

### Time & Scheduling Module ✅ (NEW)
- [x] Clock in/out functionality with location tracking
- [x] Break start/end tracking
- [x] Shift scheduling
- [x] Rota management (create, publish, copy)
- [x] Timesheet generation from clock events
- [x] Timesheet approval workflow
- [x] Attendance reporting

### Payroll Module ✅
- [x] Pay run creation and management
- [x] UK tax calculations (PAYE, NI, Student Loan)
- [x] PDF payslip generation
- [x] Guided payroll flow wizard

### HMRC RTI Sync Engine ✅
- [x] Event-driven architecture for RTI submissions
- [x] Sandbox/Live modes with SOAP/XML GovTalk envelope
- [x] FPS (Full Payment Submission) generation
- [x] Human-in-the-loop approval workflow
- [x] Poll endpoint for submission status

### UKVI Compliance Layer ✅
- [x] UKVI Compliance Dashboard
- [x] Visa expiry tracking and alerts
- [x] Compliance scoring per employee

### Right to Work (RTW) Module ✅ (NEW)
- [x] RTW check recording (manual, IDVT, Home Office, share code)
- [x] Document type validation
- [x] RTW status tracking (valid, expiring_soon, expired, not_checked)
- [x] Follow-up date calculation (28 days before expiry)
- [x] RTW summary dashboard
- [x] Bulk status update

### Certificate of Sponsorship (CoS) Register ✅ (NEW)
- [x] CoS record management
- [x] SOC code lookup with going rates
- [x] Salary threshold checks
- [x] CoS assignment to employees
- [x] Expiry tracking

### Pension Auto-Enrolment Module ✅ (NEW)
- [x] Pension scheme management
- [x] Worker category assessment (eligible, non-eligible, entitled)
- [x] Auto-enrolment logic
- [x] Opt-out recording
- [x] Contribution calculations
- [x] Contribution reports per pay run

### Enterprise Features ✅
- [x] Advanced RBAC with 45 granular permissions
- [x] 7 pre-defined role templates + custom roles
- [x] Multi-entity organization management
- [x] SCIM 2.0 provisioning endpoints
- [x] SAML SSO configuration

### AI Copilot ✅
- [x] AI-powered assistant using GPT-4o
- [x] Integration with emergentintegrations library

---

## API Endpoints

### Time & Scheduling
- `POST /api/time/clock-in` - Clock in
- `POST /api/time/clock-out` - Clock out
- `POST /api/time/break/start` - Start break
- `POST /api/time/break/end` - End break
- `GET /api/time/status` - Get clock status
- `GET /api/time/shifts` - List shifts
- `POST /api/time/shifts` - Create shift
- `GET /api/time/rotas` - List rotas
- `POST /api/time/rotas` - Create rota
- `GET /api/time/timesheets` - List timesheets
- `POST /api/time/timesheets/{id}/approve` - Approve timesheet

### Right to Work
- `POST /api/rtw/check` - Record RTW check
- `GET /api/rtw/employees/{id}` - Get employee RTW checks
- `GET /api/rtw/summary` - RTW status summary
- `GET /api/rtw/expiring` - Expiring RTW

### Certificate of Sponsorship
- `GET /api/cos` - List CoS records
- `POST /api/cos` - Create CoS
- `GET /api/cos/{id}` - Get CoS details
- `POST /api/cos/{id}/assign` - Assign CoS to employee
- `GET /api/cos/salary-checks` - Check salary thresholds
- `GET /api/cos/soc-codes/search` - Search SOC codes

### Pensions
- `GET /api/pensions/schemes` - List pension schemes
- `POST /api/pensions/schemes` - Create scheme
- `POST /api/pensions/assess` - Run bulk assessment
- `POST /api/pensions/enrolment` - Enrol employee
- `GET /api/pensions/contribution-report/{payRunId}` - Get contributions

---

## Placeholder Credentials (Replace with your own)

### In `/app/backend/.env`:
```
RESEND_API_KEY=           # Your Resend API key for email notifications
HMRC_GATEWAY_ID=          # Your HMRC Government Gateway User ID
HMRC_GATEWAY_PASSWORD=    # Your HMRC Government Gateway Password
HMRC_SENDER_ID=           # Your HMRC Sender ID (optional, defaults to Gateway ID)
```

---

## Remaining Tasks (Backlog)

### P1 - High Priority
- [ ] Statutory Payments (SSP, SMP, SPP, ShPP, SAP)
- [ ] Student Loan Deductions enhancement
- [ ] P60, P45, P11D Generation
- [ ] Benefits in Kind Module
- [ ] Employee Termination/Offboarding Workflow

### P2 - Medium Priority
- [ ] Enhanced UKVI Reporting Workflow (automated triggers)
- [ ] HMRC Settings Enhancement (PAYE ref validation in onboarding)
- [ ] Record Retention Enforcement
- [ ] Company Settings - Sponsor Licence fields

### P3 - Future
- [ ] Mobile app
- [ ] Webhook integrations
- [ ] API rate limiting
- [ ] Two-factor authentication

---

## Technical Architecture

### Backend
- FastAPI (Python)
- MongoDB (Motor async driver)
- JWT Authentication
- ReportLab (PDFs)
- httpx (HMRC submissions)

### Frontend
- React 18
- Shadcn UI + Tailwind CSS
- React Router v6

### Directory Structure
```
/app/backend/
├── routes/
│   ├── auth.py
│   ├── hmrc.py
│   ├── rti_sync.py
│   ├── ukvi.py
│   ├── enterprise.py
│   ├── time.py
│   ├── rtw.py
│   ├── cos.py
│   ├── pensions.py
│   └── self_service.py
├── services/
│   ├── rti_sync_service.py
│   ├── ukvi_service.py
│   ├── enterprise_service.py
│   ├── time_service.py
│   ├── rtw_service.py
│   ├── cos_service.py
│   ├── pension_service.py
│   └── email_service.py
└── server.py
```

---

*Last Updated: April 29, 2026*
