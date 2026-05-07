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

## NEW (May 7, 2026 — Iteration 11)

### Stripe Customer Portal ✅
- `POST /api/payments/portal` (owner only) creates a Stripe Billing Portal session using the stripe SDK directly
- Captures `stripe_customer_id` from successful checkout sessions and mirrors it to `companies.stripe_customer_id` for fast future lookups; falls back to resolving via the most recent paid transaction if missing
- "Manage subscription & payment methods" button on BillingPage (only shown when subscription_active=true)
- Lets customers self-serve: update card, switch plan, cancel subscription, download invoices

### Team Management (Invite + Roles) ✅
- `POST /api/users/invite` — owner/admin can invite by email+role (7-day token expiry, sent via Resend mock email)
- `GET /api/users/invite/{token}` (public, no auth) — preview invite details before accepting
- `POST /api/users/invite/accept` (public) — new user sets password, gets JWT back, can sign in
- `GET /api/users` — list company users; `PUT /api/users/{id}/role` (owner only); `DELETE /api/users/{id}` (owner only)
- `GET /api/users/invites` / `DELETE /api/users/invites/{id}` — manage pending invites
- Safety: self-demote blocked, self-remove blocked, owner-to-owner removal blocked, invite duplicates blocked

### Admin Portal Page (/admin) ✅
- Role-gated: only owner + admin can access; lower roles see "Access restricted" card
- 4 tabs: **Team** (user list with inline role dropdown + remove), **Invites** (pending list with revoke), **Audit Log** (last 50 events), **Danger Zone** (run retention + clear demo)
- "Invite user" button opens dialog with name/email/role form (6 roles: admin, hr_manager, payroll_admin, manager, employee, viewer)
- Copies invite link to clipboard on successful send

### Invite Accept Page (/invite/:token) ✅
- Public, no-auth page accessed via email link
- Shows company + inviter + assigned role; accept with password
- On success: stores JWT in localStorage, redirects to /dashboard

### Enhanced Onboarding Wizard ✅
- Complete step now shows an 8-module "What's next" grid linking to HMRC, UKVI, Statutory, Time Tracking, Year-End, Admin, Billing, Settings
- Each module card is clickable → instant deep link

### Sidebar Role Filtering ✅
- Admin link shown only to owner/admin roles
- Billing link shown only to owner role
- Employee/HR/Payroll roles see only the relevant modules

### Pre-Existing Bug Fixed (found by testing agent) ✅
- `POST /api/auth/register` returned 500 due to ObjectId leaking into Pydantic User model (after `User` was updated to `extra="allow"` in iter10). Fixed by popping `_id` alongside `password_hash`.

---

## NEW (May 7, 2026 — Iteration 10)

### Public Landing Page + No-Signup Sandbox Demo ✅
- New marketing landing at `/` — replaces previous `/` → `/login` redirect
- Hero + Features + Pricing + Compliance sections with gradient dark theme
- **"Try Demo" CTA** → one-click `/api/demo/sandbox` (zero auth) → instant tenant with 6 seeded employees, draft pay run, UKVI alerts, HMRC refs, pre-filled PAYE
- Sandbox JWT lasts 24 hours, user flagged `is_sandbox=true` and `auth_method='sandbox'`
- Sandbox banner in MainLayout ("You're in a sandbox demo. Data wiped after 24h — create a real account to keep it")
- Auto-cleanup via APScheduler (hourly)

### Wire Student Loan into Payroll Engine ✅
- `create_pay_run` now imports `student_loan_service.calculate_loan_deduction` and persists `student_loan_deduction` + `student_loan_plan` on each payslip
- Verified: £45k salary on Plan 2 + Postgrad → £252.79/month deducted; non-loan employees → £0

### APScheduler — Auto-cron Jobs ✅
- `services/scheduler_service.py` starts on FastAPI startup
- Jobs: `ukvi_alerts_daily` (02:00 cron — generates visa + salary threshold alerts for all companies), `sandbox_cleanup_hourly` (purges expired demo tenants), `retention_audit_weekly` (Sun 03:00)
- APScheduler 3.11.2 added to requirements.txt
- Graceful shutdown on uvicorn reload

### Axios Global Auth Interceptor ✅
- Attaches `Authorization: Bearer <token>` from localStorage on every request
- Enables sandbox token flow without per-call manual headers
- Backend continues to accept both cookie session and Bearer auth

### User Model — Expose Sandbox Flags ✅
- `GET /api/auth/me` now returns `auth_method`, `is_sandbox`, `sandbox_expires_at`
- Enables the "sandbox expiring in Xh" banner without a second round-trip

### Regression Fix (found + fixed by testing agent) ✅
- `ukvi_service.generate_expiry_alerts` crashed 500 when `immigration_status=None` (legitimately persisted by the new EmployeeCreate model) — fixed with `.get('immigration_status') or {}` safeguards

---

## NEW (May 6, 2026 — Iteration 9)

### Demo Tour Walkthrough ✅
- One-click "Start Demo Tour" on Dashboard seeds 6 demo employees (incl. 1 sponsored worker), a draft pay run with 6 payslips, and a leave request
- Floating tour overlay walks user through 6 steps: Dashboard → Employees → Payroll → Statutory → UKVI → Billing
- Idempotent seed (re-running keeps employee count at 6); one-click "Clear Demo Data" reset
- Tour state persisted in localStorage so it survives navigation; auto-mounted in MainLayout

### Student Loan Plans (P1) ✅
- 2025-26 thresholds for Plans 1/2/4/5 + Postgraduate Loan
- `services/student_loan_service.py` calculates per-period deductions
- API: `GET /api/admin/student-loans/plans`
- Employee model now accepts `student_loan_plan` and `has_postgrad_loan`

### Statutory ShPP & SAP (P1) ✅
- Shared Parental Pay (up to 37 weeks) at £184.03 / 90% AWE
- Adoption Pay (39 weeks total: 6 weeks at 90% AWE + 33 weeks at £184.03)
- Recovery rates (92% standard / 103% small employer)
- API: `POST /api/statutory/shpp/calculate`, `POST /api/statutory/sap/calculate`
- Frontend: 5-tab calculator (SSP/SMP/SPP/ShPP/SAP) at `/statutory`

### Year-End Close (P1) ✅
- Preview totals, EPS recovery, last-pay-date check
- One-click close: queues P60s for all active employees, marks final FPS, creates EPS submission record
- Auditable via `audit_log` collection
- Frontend: dedicated `/year-end` page

### Benefits in Kind / P11D UI (P1) ✅
- Inline benefits editor on Employee Detail → Actions → Benefits / P11D
- Categories: company car, fuel, medical, loan, accommodation, vouchers, expenses, other
- Auto-calculates total cash equivalent + Class 1A NIC (13.8%)
- Save record + download PDF in one dialog

### Sponsor Licence + PAYE Validation (P2) ✅
- Settings → Company tab now has dedicated HMRC References section (PAYE ref + AOR + small employer toggle)
- UKVI Sponsor Licence section (number, expiry, A/B/suspended rating)
- Server-side regex validation for PAYE format `NNN/AANNNNNNN` and AOR format `NNNPAANNNNNNNN`
- 400 error with helpful message on invalid format

### UKVI Salary Threshold Monitoring (P2) ✅
- `POST /api/ukvi/alerts/generate` now also creates `salary_threshold_breach` alerts when sponsored worker salary < CoS going-rate (or default £38,700)
- Triggers for visa types: skilled_worker, tier2, gbm, scale_up, intra_company

### Record Retention Enforcement (P2) ✅
- API: `GET /api/admin/retention/policy`, `POST /api/admin/retention/run?dry_run=true|false`
- HMRC-compliant 6-7 year retention windows for audit_log, payslips, RTI submissions, tax docs, P11D records, leave, UKVI alerts, notifications
- Owner-only access; archives to `{collection}_archive` before deletion

### API Surface Improvements ✅
- `Company` Pydantic model now exposes paye_reference, accounts_office_reference, sponsor_licence_*, small_employer_relief, demo_mode (was previously stripped)
- `EmployeeCreate` + PUT `/api/employees/{id}` allowed_fields now accept `immigration_status`, `ni_letter`, `student_loan_plan`, `has_postgrad_loan`, `pension_enrolled`, `leaving_date`, `termination_reason`

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
