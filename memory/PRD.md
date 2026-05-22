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

## NEW (May 22, 2026 — Iteration 13) — Launch-Ready Multi-Tenant SaaS

### Stripe Receipt Downloads ✅
- `_process_successful_payment` now captures `stripe_customer_id`, `payment_intent_id`, and `receipt_url` from Stripe directly via SDK
- `GET /api/payments/transactions/{transaction_id}/receipt` returns the Stripe-hosted receipt URL (or lazily fetches it)
- BillingPage transaction history has per-row "Receipt" download link

### Plan-Based Monthly Download Quota ✅
- `PLAN_DOWNLOAD_QUOTA = {starter:5, professional:50, enterprise:-1}` (server-immutable)
- DownloadGateService order: sandbox → trial → single-use pass → bulk-pass window → plan quota → £5 paywall
- `GET /api/payments/usage/this-month` returns current quota state
- BillingPage shows "Download usage — YYYY-MM" card with used/remaining/bulk-pass indicator

### Bulk Download Pass (£29 / 30 days) ✅
- New addon `bulk_downloads_monthly` — unlimited downloads for 30 days
- Stacks if already active (extends end date)
- PaywallModal upsell — when single £5 paywall hits, user sees "Or £29 unlimited 30 days" with "Best value" badge
- payslipDownload.js routes to either single or bulk Stripe checkout based on user's choice

### P45/P60/P11D Paywall ✅
- `_gate_or_402` helper applied to all three tax-document endpoints
- Identical gating: trial blocks, quota consumed, bulk pass honoured, single-use passes recognised
- Resource IDs use `p45:{emp}` / `p60:{emp}:{year}` / `p11d:{emp}:{year}` naming

### server.py Refactor ✅
- `/api/leave` POST/GET/PUT moved to `routes/leave.py`
- `/api/documents` POST/GET moved to `routes/documents.py`
- Shared helpers (`create_audit_entry`, `create_notification`) extracted into `services/audit_service.py`
- 100% backward-compatible — endpoints work identically

### Performance Management ✅
- `routes/performance.py` — Appraisals (cycle + period + 4-tier rating), SMART Objectives (with weight + progress slider), Review Notes (with `private` flag visible to HR/manager only)
- Frontend `/performance` page with 3 tabs (Objectives / Appraisals / Notes)

### Employee Relations (Disciplinary + Grievance) ✅
- `routes/employee_relations.py` — Cases module with case_types (disciplinary, grievance, performance_improvement, investigation), statuses (open → investigating → hearing → decision → closed → appealed), ACAS severity stages (informal → verbal → written_first → written_final → summary_dismissal)
- Auto-generated `case_number` (ER-YYYYMMDD-XXXX)
- Timeline events on each case
- HR/Admin/Owner only access
- Frontend `/cases` page with table + create dialog + view dialog + close-with-outcome

### Secured Document Storage ✅
- `POST /api/cases/secure-docs` — base64 upload with SHA-256 integrity check, 10MB cap
- `GET /api/cases/secure-docs/{id}/download` — logs access in audit_log + appends to per-document `access_log`
- Categories: contract, policy, nda, personnel_file, case_evidence, other
- Currently stored in MongoDB (production path: object storage — documented in LAUNCH_READINESS.md)

### Super Admin Portal ✅
- `routes/super_admin.py` — platform owner control plane
- Gating: `is_platform_admin=true` on user OR email in `PLATFORM_ADMINS` env
- Endpoints: `/metrics` (8 metrics including MRR), `/companies` (list + filter + search), `/companies/{id}` (detail with users + recent txs), `/companies/{id}/suspend|restore`, `/feature-flags` (global + company-scoped), `/impersonate` (30-min JWT with `is_impersonation=true` + full audit trail), `/audit-log`, `/emergency/kill-switch`
- Frontend `/super-admin` page with 8-metric grid + searchable company table + audit log tab + impersonate/suspend/restore actions + emergency kill switch button

### Role-based Sidebar Gating ✅
- Performance — visible to everyone
- Cases — HR/admin/owner only (`hrOnly: true`)
- Admin — admin/owner (`adminOnly: true`)
- Super Admin — platform admin only (`platformAdminOnly: true`)
- Billing — owner only (`ownerOnly: true`)

### Launch Readiness Audit ✅
- `/app/memory/LAUNCH_READINESS.md` — 🟢 PASS / 🟡 PARTIAL / 🔴 BLOCKER columns
- Maps every module against UK regulation (HMRC RTI 2025-26, Pensions Act 2008, UKVI, ACAS, GDPR, Equality Act, ERA 1996)
- Final verdict: **GO with 3 pre-launch blockers** (live Stripe key, live Resend key, live APP_URL + PLATFORM_ADMINS configured)

### Fix from testing agent ✅
- Secure-docs upload returned 500 due to ObjectId leak — fixed (`doc.pop('_id', None)` + sanitised response)

---

## NEW (May 8, 2026 — Iteration 12)

### 7-Day Free Trial ✅
- Auto-starts on `POST /api/auth/register` when `company_name` is provided — sets `trial_active=true`, `trial_started_at`, `trial_ends_at` (+7 days)
- `GET /api/trial/status` returns `{trial_active, days_remaining, trial_ends_at, subscription_active, downloads_allowed}`
- All payslip/PDF downloads blocked during trial (HTTP 403 with upgrade message)
- Stripe checkout for paid downloads also blocked during trial (so user doesn't pay £5 they can't redeem)
- TrialBanner mounts in MainLayout — yellow until 3 days left, red ≤3 days, dismiss button + "Upgrade to unlock" link to /billing
- Auto-cron daily at 09:00 UTC sends a "trial ends in 3 days" email reminder to company owners (idempotent via `trial_reminder_sent` flag)
- Subscription activation clears the trial naturally (TrialService checks for paid subscription_transactions)

### £5 Per-Payslip Download Paywall ✅
- After trial ends (no subscription), every payslip PDF download requires a £5 Stripe payment
- `POST /api/payments/checkout/payslip` body `{payslip_id: 'PAYRUN:EMPID' or just 'PAYRUN' for self-service, origin_url}` → returns Stripe `checkout_url` at £5 GBP
- Server-side fixed pricing (`PAYSLIP_DOWNLOAD_PRICE = 5.00` constant — frontend cannot manipulate)
- Successful payment via webhook/check_status creates a `download_passes` document (single-use, 30-min expiry, keyed by company+user+resource_id)
- Download endpoints (`/api/payroll/runs/{id}/payslips/{emp}/pdf` + `/api/self-service/payslips/{id}/pdf`) check the gate, consume the pass, then stream PDF
- HTTP 402 response with helpful message when no pass + paywall mode active
- Frontend `lib/payslipDownload.js` handles full flow: download → 402 → confirm → Stripe → return → poll status → re-download

### Sandbox Demo Bypass ✅
- Sandbox / demo companies (`is_sandbox=true` or `demo_mode=true`) bypass the £5 paywall — preserves the sales tour "feels like a real product" intent

### Scheduler — 4 cron jobs now ✅
- ukvi_alerts_daily (02:00) · sandbox_cleanup_hourly · retention_audit_weekly (Sun 03:00) · **trial_reminder_daily (09:00)** [NEW]

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
