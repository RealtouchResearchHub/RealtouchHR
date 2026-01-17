# RealtouchHR - Product Requirements Document

## Overview
RealtouchHR is a compliance-first HR & Payroll SaaS platform for UK businesses. 

**Core Differentiator:** "Compliance Autopilot" with continuous HMRC/UKVI checks and confidence scoring.

## Compliance Statement
- This software is **HMRC RTI-compatible** and **HMRC-aligned**
- HMRC does not endorse, approve, or certify payroll software
- Compliance with RTI regulations is the **employer's legal responsibility**
- This tool **enables compliance** through accurate record-keeping and timely submissions

---

## What's Been Implemented

### Stage 1 MVP ✅
- Authentication (JWT + Google OAuth)
- Dashboard with Compliance Score
- Employee Management
- Leave Management
- Document Management
- Time & Scheduling
- Payroll Hub with guided flow
- Audit Log
- Settings
- AI Copilot (GPT-4o via emergentintegrations)
- Light/Dark mode

### Phase 2 ✅
- Employee Detail with edit
- CSV Bulk Import
- PDF Payslip Generation
- HMRC Export Pack (FPS, EPS, P32)
- In-app Notifications
- Onboarding Wizard

### Phase 3 ✅ (January 17, 2026)
- **HMRC RTI Integration**
- **RTI Sync Engine** (Event-driven submission service)
- **Employee Self-Service Portal**
- **Email Notifications** (Resend - mock ready)
- **Backend Modularization**

---

## RTI Sync Engine Architecture

### Overview
The RTI Sync Engine is an event-driven service that manages HMRC RTI submissions with human-in-the-loop approval.

### Key Features
- **Event-Driven:** Triggers on PayRunApproved events
- **Modes:** Sandbox (test), Live (production), Paused
- **Workflow:** Prepare → Validate → Queue → Approve → Submit → Receipt
- **Human-in-the-Loop:** All submissions require explicit approval
- **Immutable Audit:** All actions logged with cryptographic hashes
- **Idempotency:** Prevents duplicate submissions per pay run

### Submission States
1. `preparing` - FPS/EPS being generated
2. `validation_pending` - Awaiting validation
3. `validation_failed` - Has blocking errors
4. `queued` - Ready for approval queue
5. `approval_pending` - Awaiting human approval
6. `approved` - Ready to submit
7. `submitting` - In progress
8. `submitted` - Sent to HMRC
9. `accepted` - HMRC accepted
10. `rejected` - HMRC rejected
11. `error` - System error
12. `cancelled` - Cancelled by user

### Validation Rules
Validates against HMRC RTI specifications:
- Company: PAYE reference, Accounts Office Reference
- Employees: NI number format, tax code, names
- Pay Run: dates, payslips, totals

### Security
- HMRC credentials stored in environment variables only
- Payloads stored with SHA-256 hashes
- Immutable audit ledger for all actions
- Feature flags control live submission

---

## API Endpoints

### RTI Sync Engine (New)
- GET `/api/rti-sync/status` - Engine status and configuration
- GET `/api/rti-sync/submissions` - List submissions
- GET `/api/rti-sync/submissions/{id}` - Submission detail
- POST `/api/rti-sync/prepare` - Prepare FPS
- POST `/api/rti-sync/submissions/{id}/validate` - Re-validate
- POST `/api/rti-sync/submissions/{id}/request-approval` - Request approval
- POST `/api/rti-sync/submissions/{id}/approve` - Approve (requires confirmation)
- POST `/api/rti-sync/submissions/{id}/reject` - Reject
- POST `/api/rti-sync/submissions/{id}/submit` - Submit to HMRC
- GET `/api/rti-sync/submissions/{id}/audit-trail` - Immutable audit trail
- GET `/api/rti-sync/receipts` - HMRC receipts
- GET `/api/rti-sync/health-check/{payrun_id}` - Pre-submission validation

### Self-Service Portal
- GET/PUT `/api/self-service/profile` - Employee profile
- GET `/api/self-service/payslips` - Payslip list
- GET `/api/self-service/payslips/{id}/download` - Download PDF
- GET `/api/self-service/leave/balance` - Leave balance
- GET/POST `/api/self-service/leave/requests` - Leave requests
- DELETE `/api/self-service/leave/request/{id}` - Cancel request
- GET `/api/self-service/documents` - View documents

### HMRC RTI (Legacy)
- POST `/api/hmrc/validate/{payrun_id}` - Validate
- GET `/api/hmrc/health-check/{payrun_id}` - Health check
- POST `/api/hmrc/fps/submit` - Submit FPS
- POST `/api/hmrc/eps/submit` - Submit EPS
- GET `/api/hmrc/submissions` - History

---

## Frontend Pages

- `/rti-sync` - **RTI Sync Engine Wizard** (New)
- `/hmrc` - HMRC RTI Dashboard
- `/self-service` - Employee Self-Service Portal

---

## Environment Configuration

### Required for RTI
```bash
# RTI Sync Engine Mode
RTI_SYNC_MODE=sandbox|live|paused
RTI_LIVE_SUBMISSION_ENABLED=false
RTI_AUTO_PREPARE_ENABLED=true

# HMRC Gateway (for live mode)
HMRC_GATEWAY_ID=your_gateway_id
HMRC_GATEWAY_PASSWORD=your_password
```

### Required for Email
```bash
RESEND_API_KEY=your_resend_key
SENDER_EMAIL=noreply@yourcompany.com
```

### Company Settings (via UI)
- `paye_reference` - Format: 123/ABC123
- `accounts_office_reference` - HMRC AOR
- `hmrc_sender_id` - Gateway sender ID (optional)

---

## Backend Architecture

```
/app/backend/
├── server.py                 # Main FastAPI app
├── routes/
│   ├── auth.py              # JWT/OAuth routes
│   ├── hmrc.py              # HMRC RTI routes
│   ├── self_service.py      # Employee portal
│   └── rti_sync.py          # RTI Sync Engine routes
├── services/
│   ├── email_service.py     # Resend integration
│   ├── hmrc_service.py      # HMRC helpers
│   ├── pdf_service.py       # PDF generation
│   └── rti_sync_service.py  # RTI Sync Engine
├── models/                   # Pydantic models
└── utils/                    # Helpers
```

---

## Compliance Collections (MongoDB)

- `rti_submissions` - Submission records
- `rti_payloads` - XML payloads (encrypted)
- `rti_receipts` - HMRC receipts
- `rti_audit_ledger` - Immutable audit trail

---

## Mocked/Stub Implementations

1. **Email (Resend):** Mock until RESEND_API_KEY set
2. **HMRC Gateway:** Sandbox mode returns mock responses
3. **Live HMRC:** Stub - requires credentials + feature flag

---

## Test Reports
- `/app/test_reports/iteration_4.json` (100% pass)

## Credentials
- Email: test@example.com
- Password: Test123!

---

*Last Updated: January 17, 2026*
