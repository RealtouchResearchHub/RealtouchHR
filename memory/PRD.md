# RealtouchHR - Product Requirements Document

## Overview
RealtouchHR is a next-generation HR, Payroll, and Compliance SaaS platform designed for the UK market with global extensibility. The platform provides comprehensive tools for employee management, payroll processing, compliance monitoring, and regulatory submissions.

## Core Differentiation
- **Compliance Autopilot**: Real-time risk scoring and automated compliance monitoring
- **One Guided Payroll Flow**: Intuitive payroll processing with RTI integration
- **AI Copilots**: Intelligent assistance for various HR tasks
- **UK-First Design**: HMRC RTI, UKVI compliance, UK tax calculations

## Target Market
- UK businesses of all sizes
- Companies with sponsored workers (UKVI compliance)
- Multi-entity organizations requiring consolidated reporting

---

## Implemented Features

### Authentication & User Management
- [x] JWT-based authentication (email/password)
- [x] Emergent-managed Google Social Login
- [x] Role-based access control (Owner, Admin, HR Manager, Payroll Admin, Manager, Employee)
- [x] User registration and onboarding wizard

### Core HR Module
- [x] Employee records management (CRUD)
- [x] Employee detail views with compliance scoring
- [x] Bulk employee import (CSV)
- [x] Leave management and approval workflows
- [x] Document management and storage

### Payroll Module
- [x] Pay run creation and management
- [x] UK tax calculations (PAYE, NI, Student Loan)
- [x] PDF payslip generation
- [x] Multi-currency support (16+ currencies)
- [x] Guided payroll flow wizard

### HMRC RTI Sync Engine (P0 - COMPLETED)
- [x] Event-driven architecture for RTI submissions
- [x] Sandbox/Live/Paused modes
- [x] FPS (Full Payment Submission) generation
- [x] Human-in-the-loop approval workflow
- [x] Immutable audit trails
- [x] SOAP/XML GovTalk envelope for live HMRC submissions
- [x] Poll endpoint for submission status tracking
- [x] Correlation ID tracking

### UKVI Compliance Layer (P2 - COMPLETED)
- [x] UKVI Compliance Dashboard
- [x] Employee visa/immigration tracking
- [x] Visa expiry alerts and notifications
- [x] Right-to-work monitoring
- [x] Appendix D record completeness tracking
- [x] Reportable events detection (10-day reporting)
- [x] Reporting checklist with deadlines
- [x] Compliance scoring per employee

### Enterprise Features (P2 - COMPLETED)
- [x] Advanced RBAC with 45 granular permissions
- [x] 7 pre-defined role templates
- [x] Custom role creation
- [x] Multi-entity organization management
- [x] Consolidated payroll reporting
- [x] SCIM 2.0 provisioning endpoints
- [x] SAML SSO configuration

### AI Copilot
- [x] AI-powered assistant using GPT-4o
- [x] Integration with emergentintegrations library
- [x] Contextual HR queries and assistance

### Self-Service Portal
- [x] Employee profile view
- [x] Payslip access
- [x] Leave request submission
- [x] Personal document access

---

## Technical Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB (Motor async driver)
- **Authentication**: JWT tokens
- **PDF Generation**: ReportLab
- **Email Service**: Resend (stubbed)
- **HMRC Integration**: SOAP/XML via httpx

### Frontend
- **Framework**: React 18
- **UI Library**: Shadcn UI + Tailwind CSS
- **State Management**: Context API
- **Routing**: React Router v6

### Directory Structure
```
/app/
├── backend/
│   ├── models/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── hmrc.py
│   │   ├── rti_sync.py
│   │   ├── ukvi.py
│   │   ├── enterprise.py
│   │   └── self_service.py
│   ├── services/
│   │   ├── email_service.py
│   │   ├── hmrc_service.py
│   │   ├── pdf_service.py
│   │   ├── rti_sync_service.py
│   │   ├── ukvi_service.py
│   │   └── enterprise_service.py
│   └── server.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── pages/
│       │   └── shared/
│       └── App.js
└── memory/
    └── PRD.md
```

---

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/token` - Token refresh

### Employees
- `GET /api/employees` - List employees
- `POST /api/employees` - Create employee
- `GET /api/employees/{id}` - Get employee details
- `PUT /api/employees/{id}` - Update employee

### Payroll
- `GET /api/pay-runs` - List pay runs
- `POST /api/pay-runs` - Create pay run
- `GET /api/pay-runs/{id}` - Get pay run details

### RTI Sync
- `GET /api/rti-sync/status` - Engine status
- `GET /api/rti-sync/submissions` - List submissions
- `POST /api/rti-sync/prepare` - Prepare FPS
- `POST /api/rti-sync/submissions/{id}/approve` - Approve submission
- `POST /api/rti-sync/submissions/{id}/submit` - Submit to HMRC
- `POST /api/rti-sync/submissions/{id}/poll` - Poll HMRC status

### UKVI Compliance
- `GET /api/ukvi/dashboard` - Company UKVI dashboard
- `GET /api/ukvi/visa-types` - Visa type reference
- `GET /api/ukvi/alerts` - Active alerts
- `GET /api/ukvi/reporting/checklist` - Pending reports

### Enterprise
- `GET /api/enterprise/roles` - Company roles
- `POST /api/enterprise/roles` - Create custom role
- `GET /api/enterprise/permissions` - All permissions
- `GET /api/enterprise/sso/config` - SSO configuration

---

## Database Collections
- `users` - User accounts
- `companies` - Company records
- `employees` - Employee records
- `pay_runs` - Payroll runs
- `payslips` - Individual payslips
- `leave_requests` - Leave applications
- `audit_log` - System audit trail
- `rti_submissions` - RTI submission records
- `rti_audit_ledger` - RTI audit entries
- `rti_receipts` - HMRC receipts
- `ukvi_alerts` - UKVI compliance alerts
- `ukvi_reporting_events` - Reportable events
- `roles` - Custom role definitions
- `organizations` - Multi-entity orgs
- `entities` - Legal entities
- `sso_configs` - SSO settings

---

## Mocked/Stubbed Services
1. **HMRC Live Submission**: Credentials required (HMRC_GATEWAY_ID, HMRC_GATEWAY_PASSWORD)
2. **Email Notifications**: API key required (RESEND_API_KEY)
3. **SCIM IdP Integration**: Endpoint available, requires IdP setup
4. **SAML SSO**: Endpoint available, requires IdP metadata

---

## Test Coverage
- Backend: 100% API tests passing
- Frontend: 100% E2E tests passing
- Test files: `/app/backend/tests/`, `/app/tests/e2e/`

---

## Future Roadmap

### Backlog
- [ ] Time & Scheduling module (rotas, clock-ins)
- [ ] E-signature integration
- [ ] Advanced analytics dashboard
- [ ] Mobile app
- [ ] Webhook integrations
- [ ] API rate limiting
- [ ] Two-factor authentication

---

*Last Updated: April 29, 2026*
