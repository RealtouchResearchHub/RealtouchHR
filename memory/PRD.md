# RealtouchHR - Product Requirements Document

## Overview
RealtouchHR is a next-generation HR, Payroll, and Compliance SaaS platform designed for the UK market with global extensibility. The user plans to deploy on Namecheap (frontend + backend).

---

## Implemented Features

### Core HR Module ✅
- Employee CRUD, detail views with compliance scoring, bulk CSV import
- Leave management and approval workflows
- Document management

### Authentication ✅
- JWT-based (email/password) + Emergent-managed Google Social Login
- Role-based access control

### Time & Scheduling ✅
- Clock in/out with location, breaks, shifts, rotas, timesheet generation/approval, attendance reporting

### Payroll ✅
- Pay run creation, UK PAYE/NI/Student Loan calculations
- PDF payslip generation, guided payroll flow

### HMRC RTI Sync ✅
- Live SOAP submission via `zeep` (sandbox/live modes), FPS generation, human-in-the-loop approval

### UKVI Compliance ✅
- Visa expiry tracking, compliance scoring, alerts dashboard

### Right to Work (RTW) ✅
- Manual / IDVT / Home Office / share code checks, expiry tracking, follow-up dates

### Certificate of Sponsorship (CoS) ✅
- CoS register, SOC code lookup, salary threshold checks, employee assignment

### Pension Auto-Enrolment ✅
- Scheme management, worker category assessment, opt-out, contribution reports

### Enterprise ✅
- 45 RBAC permissions, 7 role templates, multi-entity, SCIM 2.0, SAML SSO

### AI Copilot ✅
- GPT-4o powered assistant via emergentintegrations Universal Key

---

## NEW (May 6, 2026 — Iteration 8)

### Stripe Subscription Billing ✅
- Plans: Starter (£49/mo, 10 employees), Professional (£149/mo, 50), Enterprise (£399/mo, unlimited)
- One-time add-ons: Extra users (+10), Priority support, Data migration
- Server-side fixed pricing (no frontend amount manipulation)
- `payment_transactions` collection — pending → paid lifecycle
- Polling on return from Stripe, owner-only billing access
- Top-level webhook at `/api/webhook/stripe`
- Dedicated `/billing` page with plan cards + add-ons + transaction history

### Statutory Payments (SSP/SMP/SPP) ✅
- 2025-26 rates: SSP £116.75/wk, SMP/SPP £184.03/wk, LEL £123/wk
- Calculator UI for SSP, SMP, SPP per employee
- Recovery rate calculation (92% standard / 103% small employer)
- Records persisted in `statutory_payments` collection
- `/api/statutory/eps-summary` for EPS submission

### P45 / P60 / P11D PDF Generation ✅
- Auto-generated P45 on employee offboarding
- On-demand P60 download for any tax year
- P11D benefits-in-kind records + downloadable PDF
- Endpoints: `/api/tax-docs/p45/{id}`, `/p60/{id}?tax_year=YYYY-YY`, `/p11d/{id}/{tax_year}`

### Employee Offboarding/Termination Workflow ✅
- Wizard dialog accessible via Actions dropdown on Employee Detail
- Atomic pipeline: mark leaver → generate P45 → queue RTI leaver → trigger UKVI report (if sponsored) → cease pension → email confirmation
- 8 termination reasons (resignation, dismissal, redundancy, retirement, end-of-contract, TUPE, death, visa refusal)

### Email Notifications ✅
- Visa expiry alerts (UKVI alert generation)
- Timesheet approval/rejection (with reason)
- Pension auto-enrolment confirmation (with opt-out window)
- Subscription confirmation
- Leave approval/rejection (existing)
- Currently in MOCK mode — set `RESEND_API_KEY` in `/app/backend/.env` to enable

---

## API Endpoints (New in Iter 8)

### Billing/Stripe
- `GET /api/payments/plans`, `GET /api/payments/billing`, `GET /api/payments/transactions`
- `POST /api/payments/checkout/subscription`, `POST /api/payments/checkout/addon`, `POST /api/payments/checkout/status`
- `POST /api/webhook/stripe` (top-level for Stripe webhooks)

### Statutory
- `GET /api/statutory/rates`
- `POST /api/statutory/{ssp|smp|spp}/calculate`
- `POST /api/statutory/record`
- `GET /api/statutory/{employee/{id}|active|eps-summary}`

### Offboarding
- `GET /api/offboarding/reasons`, `GET /api/offboarding/list`
- `POST /api/offboarding/terminate`, `POST /api/offboarding/reinstate/{id}`

### Tax Documents
- `GET /api/tax-docs/p45/{employee_id}`
- `GET /api/tax-docs/p60/{employee_id}?tax_year=YYYY-YY`
- `POST /api/tax-docs/p11d`, `GET /api/tax-docs/p11d/{employee_id}/{tax_year}`
- `GET /api/tax-docs/employee/{employee_id}/documents`

---

## Placeholder Credentials

`/app/backend/.env`:
```
RESEND_API_KEY=           # Empty → mock email mode (intentional)
HMRC_GATEWAY_ID=          # Placeholder for sandbox SOAP
HMRC_GATEWAY_PASSWORD=
HMRC_SENDER_ID=
STRIPE_API_KEY=sk_test_emergent  # Pod test key — already configured
EMERGENT_LLM_KEY=sk-emergent-...   # Universal Key for GPT-4o copilot
```

---

## Backlog

### P1 — High Priority
- Student Loan deductions enhancement (Plans 1/2/4/5 + Postgrad)
- Benefits in Kind ingestion form (UI for adding P11D items)
- Year-end FPS finalization + EPS auto-generation (annual close)
- ShPP / SAP calculators (currently SSP/SMP/SPP only — service code already supports them)

### P2 — Medium Priority
- Company Settings — Sponsor Licence fields, PAYE-ref validation in onboarding
- Record Retention enforcement (auto-archive after retention window)
- UKVI salary threshold monitoring (alert on going-rate drift)
- Real-time multi-entity payroll consolidation

### P3 — Future
- Mobile app, webhook integrations, API rate limiting, 2FA
- Refactor `server.py` (~2.9K lines) into smaller modules under `routes/`

---

## Technical Architecture

### Backend (FastAPI / MongoDB)
```
/app/backend/
├── routes/
│   ├── auth.py, hmrc.py, rti_sync.py, ukvi.py, enterprise.py
│   ├── time.py, rtw.py, cos.py, pensions.py, self_service.py
│   ├── payments.py, statutory.py, offboarding.py, tax_documents.py   ← NEW
├── services/
│   ├── email_service.py (with visa/timesheet/pension/subscription helpers)
│   ├── hmrc_service.py, rti_sync_service.py, ukvi_service.py
│   ├── enterprise_service.py, time_service.py, rtw_service.py
│   ├── cos_service.py, pension_service.py
│   ├── payment_service.py, statutory_service.py, offboarding_service.py   ← NEW
│   └── pdf_service.py (now generates P45/P60/P11D in addition to payslips)
└── server.py (top-level router + /api/webhook/stripe)
```

### Frontend (React + Shadcn + Tailwind)
```
/app/frontend/src/components/
├── pages/
│   ├── BillingPage.jsx          ← NEW: /billing
│   ├── StatutoryPaymentsPage.jsx ← NEW: /statutory
│   ├── (existing 18 pages…)
└── shared/
    ├── OffboardingDialog.jsx    ← NEW
    └── (existing shared widgets)
```

---

*Last Updated: May 6, 2026 — Iteration 8 (Stripe + Statutory + Offboarding + Tax Docs + Email Notifications)*
