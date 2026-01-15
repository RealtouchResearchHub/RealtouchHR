# RealtouchHR - Product Requirements Document

## Overview
RealtouchHR is a compliance-first HR & Payroll SaaS platform for UK businesses. Core differentiator: "Compliance Autopilot" with continuous checks and confidence scoring.

## Original Problem Statement
Build a next-generation HR + Payroll + Compliance SaaS platform (UK-first) with:
- Compliance Autopilot with continuous checks
- Compliance Confidence Score per employee/pay run
- One guided payroll flow: Prepare → Validate → Preview → Approve → Export
- AI copilots for onboarding, payroll, compliance monitoring, and document drafting
- Strong RBAC and immutable audit log

## User Personas
1. **Business Owner** - Needs overview of HR compliance and payroll status
2. **HR Admin** - Manages employees, leave, documents
3. **Payroll Admin** - Runs payroll, manages pay runs, submits to HMRC
4. **Manager** - Approves leave, views team schedules
5. **Employee** - Views payslips, requests leave (via Self-Service Portal)
6. **Auditor** - Reviews audit logs, compliance reports

## Core Requirements
- JWT + Google OAuth authentication
- Employee management with compliance scoring
- Leave/absence management with calendar
- Document management with templates
- Time & scheduling (shifts, clock-in/out)
- UK payroll preview (pay runs, payslips, PAYE/NI calculations)
- HMRC RTI submissions (FPS/EPS)
- Employee Self-Service Portal
- Immutable audit log
- AI Copilot with human-in-the-loop
- Light/dark mode with user preference

---

## What's Been Implemented

### Stage 1 MVP - Complete ✅
- Authentication (JWT + Google OAuth via Emergent)
- Dashboard with Compliance Score and Next Best Action
- Employee Management (CRUD, compliance scoring)
- Leave Management (requests, approvals, calendar)
- Document Management (create, templates)
- Time & Scheduling (shifts, clock-in/out)
- Payroll Hub (guided flow, pay runs, payslips preview)
- Audit Log (immutable timeline)
- Settings (company, compliance tasks, theme)
- AI Copilot sidebar (GPT-4o via emergentintegrations)
- Light/Dark mode toggle

### Phase 2 Features - Complete ✅
- Employee Detail Page with edit functionality
- CSV Bulk Import (employees and timesheets)
- PDF Payslip Generation (individual downloads)
- HMRC Export Pack (FPS, EPS, P32 CSV exports)
- Leave Approval Notifications
- In-app Notifications System
- Time-to-First-Payroll Onboarding Wizard

### Phase 3 Features - Complete ✅ (January 15, 2026)
- **HMRC RTI Integration:**
  - Full Payment Submission (FPS) validation & submission
  - Employer Payment Summary (EPS) submission
  - Payroll Health Check before submission
  - Test mode for development (mock HMRC responses)
  - Submission history tracking
  
- **Employee Self-Service Portal:**
  - View own profile (read-only core data)
  - Update personal details (phone, address, emergency contacts, bank info)
  - View and download payslips as PDF
  - View leave balance
  - Submit and cancel leave requests
  - View documents shared with employee
  
- **Email Notifications (Resend):**
  - Mock implementation ready for Resend API key
  - Templates for: leave approval, payslip ready, compliance reminder, welcome, employee invite
  
- **Backend Modularization:**
  - Routes split into `/app/backend/routes/` (auth.py, hmrc.py, self_service.py)
  - Services in `/app/backend/services/` (email_service.py, hmrc_service.py, pdf_service.py)
  - Models in `/app/backend/models/`
  - Utilities in `/app/backend/utils/`

### Bug Fixes - January 15, 2026
- Fixed AI Copilot using emergentintegrations library
- Fixed AuthContext to expose token for fetch-based API calls
- Fixed RTIStatus class usage in HMRC routes
- Fixed compliance score display safeguards
- Added HMRC-related fields to company update endpoint

---

## API Endpoints

### Authentication
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- POST /api/auth/session (Google OAuth)
- POST /api/auth/logout
- PUT /api/auth/preferences

### Company
- GET /api/company
- PUT /api/company
- GET /api/company/email-settings
- PUT /api/company/email-settings

### Employees
- GET /api/employees
- POST /api/employees
- GET /api/employees/{id}
- PUT /api/employees/{id}
- DELETE /api/employees/{id}
- POST /api/import/employees
- GET /api/employees/import/template

### Leave
- GET /api/leave
- POST /api/leave
- PUT /api/leave/{id}
- GET /api/leave/balance/{employee_id}

### Documents
- GET /api/documents
- POST /api/documents
- GET /api/documents/{id}
- PUT /api/documents/{id}
- DELETE /api/documents/{id}
- GET /api/documents/templates

### Scheduling
- GET /api/shifts
- POST /api/shifts
- PUT /api/shifts/{id}
- DELETE /api/shifts/{id}
- POST /api/shifts/{id}/clock-in
- POST /api/shifts/{id}/clock-out
- GET /api/timesheets
- POST /api/import/timesheets

### Payroll
- GET /api/payroll/runs
- POST /api/payroll/runs
- GET /api/payroll/runs/{id}
- PUT /api/payroll/runs/{id}/approve
- GET /api/payroll/runs/{id}/payslips/{empId}/pdf
- GET /api/payroll/runs/{id}/export/fps
- GET /api/payroll/runs/{id}/export/eps
- GET /api/payroll/runs/{id}/export/p32

### HMRC RTI (New)
- POST /api/hmrc/validate/{payrun_id}
- GET /api/hmrc/health-check/{payrun_id}
- POST /api/hmrc/fps/submit
- POST /api/hmrc/eps/submit
- GET /api/hmrc/submissions
- GET /api/hmrc/submissions/{id}
- POST /api/hmrc/submissions/{id}/poll

### Self-Service Portal (New)
- GET /api/self-service/profile
- PUT /api/self-service/profile
- GET /api/self-service/payslips
- GET /api/self-service/payslips/{payrun_id}/download
- GET /api/self-service/leave/balance
- GET /api/self-service/leave/requests
- POST /api/self-service/leave/request
- DELETE /api/self-service/leave/request/{id}
- GET /api/self-service/documents
- GET /api/self-service/documents/{id}

### Other
- GET /api/audit
- GET /api/compliance/score
- GET /api/compliance/tasks
- POST /api/compliance/tasks
- PUT /api/compliance/tasks/{id}
- POST /api/copilot/chat
- GET /api/notifications
- GET /api/onboarding/progress
- PUT /api/onboarding/progress
- GET /api/currencies
- GET /api/currencies/convert
- GET /api/dashboard/stats
- GET /api/health

---

## Frontend Pages

### Public
- /login - Login page (JWT + Google OAuth)
- /register - Registration page

### Protected (with MainLayout)
- /dashboard - Main dashboard with stats
- /employees - Employee directory
- /employees/:id - Employee detail & edit
- /leave - Leave management
- /documents - Document management
- /scheduling - Shifts & rotas
- /payroll - Payroll hub
- /payroll/:id - Pay run detail with exports
- /hmrc - **HMRC RTI Dashboard (New)**
- /import - Bulk import
- /audit - Audit log
- /self-service - **Employee Self-Service Portal (New)**
- /settings - Company settings

### Protected (without MainLayout)
- /onboarding - Onboarding wizard

---

## Tech Stack
- **Backend:** FastAPI + MongoDB (motor async) + reportlab (PDF)
- **Frontend:** React + Shadcn UI + Tailwind CSS
- **Auth:** JWT + Emergent Google OAuth
- **AI:** OpenAI GPT-4o (via emergentintegrations with Emergent LLM key)
- **Email:** Resend (mock until API key provided)

---

## Prioritized Backlog

### P0 - Critical
- [ ] Connect HMRC RTI to production gateway (requires HMRC credentials)

### P1 - High Priority
- [ ] Full Resend email integration (add API key)
- [ ] Advanced RBAC with custom roles
- [ ] Working time directive checks
- [ ] Real-time HMRC validation API

### P2 - Medium Priority
- [ ] Multi-entity/company support
- [ ] SCIM/SAML SSO integration
- [ ] Mobile responsive optimizations
- [ ] Holiday calendar integration
- [ ] Pension auto-enrollment workflow
- [ ] Student loan deductions

### P3 - Refactoring
- [ ] Add comprehensive unit tests (pytest)
- [ ] Implement rate limiting
- [ ] Add API documentation (Swagger/OpenAPI)

---

## Test Reports
- /app/test_reports/iteration_1.json
- /app/test_reports/iteration_2.json
- /app/test_reports/iteration_3.json
- /app/test_reports/iteration_4.json (Latest - 100% pass rate)

## Test Credentials
- Email: test@example.com
- Password: Test123!

---

## Mocked/Placeholder Implementations

1. **Email Notifications (Resend)**
   - Currently uses mock implementation
   - Set `RESEND_API_KEY` in `/app/backend/.env` to enable real emails
   
2. **HMRC Gateway Submission**
   - TEST MODE only - generates mock XML and returns simulated success
   - Production requires HMRC Gateway credentials in company settings

---

## Configuration Required for Production

1. **Environment Variables:**
   - `RESEND_API_KEY` - For email notifications
   - `SENDER_EMAIL` - From address for emails
   
2. **Company Settings (via Settings page):**
   - `paye_reference` - HMRC PAYE reference (format: 123/ABC123)
   - `accounts_office_reference` - HMRC Accounts Office Reference
   - `hmrc_sender_id` - HMRC Gateway sender ID
   - `hmrc_password` - HMRC Gateway password

---

*Last Updated: January 15, 2026*
