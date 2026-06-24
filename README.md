# RealtouchHR

**UK Payroll, HR & Compliance — all in one platform.**

RealtouchHR is a full-stack SaaS application built for UK small and medium businesses. It handles HMRC-ready payroll with RTI submissions, right-to-work and UKVI immigration compliance, GDPR data protection, employee lifecycle management, and more — replacing spreadsheets and external consultants for under £29/month.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Deployment (Render)](#deployment-render)
- [Authentication](#authentication)
- [Platform / Super Admin](#platform--super-admin)
- [Key Modules](#key-modules)
- [API Overview](#api-overview)
- [Email System](#email-system)
- [Demo & Sandbox](#demo--sandbox)
- [Discount / Promo Codes](#discount--promo-codes)
- [Companies House Integration](#companies-house-integration)
- [Security](#security)

---

## Features

| Module | Description |
|---|---|
| **Dashboard** | Real-time compliance score, critical actions, headcount stats, quick links |
| **Employees** | Full lifecycle — add, edit, archive, offboard. Profile photos, org chart hierarchy, line manager assignment |
| **Payroll** | Pay runs, payslips, tax & NI calculations, salary types, pay schedules |
| **HMRC / RTI** | Full RTI submission pipeline (FPS/EPS), sandbox and live modes, submission history |
| **UKVI Compliance** | Visa tracking, sponsor licence management, right-to-work checks, Home Office reporting |
| **Right to Work** | Document upload, expiry tracking, follow-up scheduling, compliance flags |
| **Leave & Absence** | Leave requests (annual, sick, maternity, etc.), manager approval workflow, absence records |
| **Documents** | Company-wide document library, employee document uploads, expiry tracking |
| **Policies** | Policy library, version control, employee acknowledgement tracking |
| **Training** | Course catalogue, mandatory training, completion records, expiry reminders |
| **Performance** | Review cycles, objectives, ratings |
| **Expenses** | Expense submissions, approvals, categories |
| **Recruitment** | Job postings, applicant tracking |
| **HR Analytics** | Compliance calendar (180-day horizon), headcount CSV export, org chart (list & tree views) |
| **GDPR / DPO Centre** | Data subject requests (DSRs), retention policies, ICO-ready audit trail, breach log |
| **Time & Scheduling** | Timesheets, shift scheduling, approval workflow |
| **Statutory Payments** | SSP, SMP, SPP calculators |
| **Self-Service Portal** | Employee-facing portal — payslips, leave requests, personal details, documents |
| **Enterprise** | Multi-entity, advanced reporting |
| **AI HR Copilot** | Anthropic-powered assistant — answers any HR/payroll/compliance question in context |
| **Billing** | Stripe-powered subscription management, plan upgrades, invoices |
| **2FA** | TOTP-based two-factor authentication with QR code setup |
| **Audit Log** | Full immutable audit trail across all actions |
| **Notifications** | In-app notification centre |
| **Year End** | P60 generation, year-end submission workflow |
| **Tax Documents** | P60, P45, P11D generation |
| **Trust Badge** | Public-facing compliance verification badge |
| **Super Admin** | Platform operator panel — companies, users, feature flags, operators, emergency controls, welcome email editor, discount codes |

---

## Tech Stack

### Backend
| | |
|---|---|
| **Framework** | FastAPI (Python 3.11+) |
| **Database** | Supabase (PostgreSQL via PostgREST + Supabase Python SDK) |
| **Auth** | JWT (PyJWT) + session cookies + Google OAuth 2.0 |
| **Email** | Resend API |
| **Payments** | Stripe |
| **AI** | Anthropic Claude (primary), OpenAI (fallback), LiteLLM |
| **HMRC RTI** | Zeep (SOAP) for RTI Gateway submissions |
| **Companies House** | REST API (HTTP Basic Auth) |
| **PDF Generation** | ReportLab |
| **Rate Limiting** | SlowAPI |
| **Scheduling** | APScheduler |
| **Server** | Uvicorn |

### Frontend
| | |
|---|---|
| **Framework** | React 19 + React Router 7 |
| **UI Library** | shadcn/ui (Radix UI primitives) |
| **Styling** | Tailwind CSS |
| **Icons** | Lucide React |
| **Charts** | Recharts |
| **HTTP Client** | Axios |
| **Forms** | React Hook Form + Zod |
| **Toast** | Sonner |
| **Build** | CRACO (Create React App) |

---

## Project Structure

```
realtouchhr/
├── backend/
│   ├── server.py               # Main FastAPI app, all core routes, auth endpoints
│   ├── database.py             # Supabase/PostgREST async adapter
│   ├── requirements.txt
│   ├── .env                    # Environment variables (never commit)
│   ├── routes/
│   │   ├── absence.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── company_lookup.py   # Companies House REST API (unauthenticated, for registration)
│   │   ├── cos.py              # Certificate of Sponsorship
│   │   ├── demo.py             # Demo seed + sandbox account creation
│   │   ├── documents.py
│   │   ├── dpo.py              # Data Protection Officer / GDPR
│   │   ├── employee_relations.py
│   │   ├── enterprise.py
│   │   ├── expenses.py
│   │   ├── fairness.py
│   │   ├── gdpr.py
│   │   ├── hmrc.py             # RTI / HMRC integration
│   │   ├── hr_analytics.py     # Compliance calendar, headcount reports, org chart
│   │   ├── leave.py
│   │   ├── offboarding.py
│   │   ├── payments.py         # Stripe billing
│   │   ├── pensions.py
│   │   ├── performance.py
│   │   ├── platform_mgmt.py
│   │   ├── policies.py
│   │   ├── recruitment.py
│   │   ├── reports.py
│   │   ├── rti_sync.py
│   │   ├── rtw.py              # Right to Work
│   │   ├── self_service.py
│   │   ├── statutory.py
│   │   ├── super_admin.py      # Platform operator panel
│   │   ├── tax_documents.py
│   │   ├── team.py
│   │   ├── time.py             # Timesheets & scheduling
│   │   ├── training.py
│   │   ├── trial.py
│   │   ├── trust_badge.py
│   │   ├── two_factor.py
│   │   ├── ukvi.py             # UKVI & immigration compliance
│   │   └── year_end.py
│   └── services/
│       ├── email_service.py    # Resend email + template system
│       ├── offboarding_service.py
│       └── scheduler_service.py
│
├── frontend/
│   ├── public/
│   │   ├── logo-dark.png
│   │   └── logo-white.png
│   └── src/
│       ├── App.js              # Routes, auth guards
│       ├── contexts/
│       │   └── AuthContext.jsx # Global auth state
│       ├── components/
│       │   ├── pages/          # One file per page/module
│       │   ├── shared/         # DemoTour, OffboardingDialog, etc.
│       │   └── ui/             # shadcn/ui component library
│       └── lib/
│           └── utils.js
│
├── render.yaml                 # Render.com deployment config
├── tests/                      # Backend test suite
└── docs/                       # Additional documentation
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+ and Yarn 1.x
- A [Supabase](https://supabase.com) project
- (Optional) Resend, Stripe, Anthropic, Companies House API keys

### 1. Clone and set up

```bash
git clone <your-repo-url>
cd realtouchhr
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy and populate the environment file:

```bash
cp .env.example .env   # or create .env manually — see Environment Variables below
```

Start the backend:

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`. Health check: `GET /api/health`

### 3. Frontend

```bash
cd frontend
yarn install
```

Create `frontend/.env`:

```
REACT_APP_BACKEND_URL=http://localhost:8001
```

Start the frontend:

```bash
yarn start
```

The app runs at `http://localhost:3000`.

---

## Environment Variables

All backend configuration lives in `backend/.env`. **Never commit this file.**

### Required

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL (`https://xxx.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (full DB access) |
| `JWT_SECRET` | Random secret for signing JWTs — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_URL` | Frontend URL (e.g. `http://localhost:3000` or production domain) |
| `PUBLIC_APP_URL` | Same as `APP_URL` in most cases |

### Optional — enables specific features

| Variable | Feature |
|---|---|
| `RESEND_API_KEY` | Transactional emails (welcome, leave approval, payslip notifications, etc.) |
| `SENDER_EMAIL` | From address for all emails (must be verified in Resend) |
| `STRIPE_API_KEY` | Subscription billing |
| `STRIPE_PUBLISHABLE_KEY` | Stripe client-side key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature verification |
| `ANTHROPIC_API_KEY` | AI HR Copilot (Claude) |
| `OPENAI_API_KEY` | AI fallback |
| `GOOGLE_CLIENT_ID` | Sign in / sign up with Google |
| `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GOOGLE_REDIRECT_URI` | Must match what's registered in Google Cloud Console (e.g. `http://localhost:8001/api/auth/google/callback`) |
| `COMPANIES_HOUSE_API_KEY` | Live company lookup at registration (Companies House REST API) |
| `PLATFORM_ADMINS` | Comma-separated emails that have Super Admin access (e.g. `you@example.com`) |
| `HMRC_GATEWAY_ID` | HMRC RTI Gateway credentials (leave blank for sandbox mode) |
| `HMRC_GATEWAY_PASSWORD` | HMRC RTI Gateway password |
| `RTI_SYNC_MODE` | `sandbox` (default) or `live` |
| `RTI_LIVE_SUBMISSION_ENABLED` | `false` (default) — set `true` to enable real HMRC submissions |
| `TOTP_ISSUER` | Label shown in authenticator apps (default: `RealtouchHR`) |

### Frontend

| Variable | Description |
|---|---|
| `REACT_APP_BACKEND_URL` | Backend base URL (e.g. `http://localhost:8001`) |

---

## Running the App

Once both servers are running:

| URL | Description |
|---|---|
| `http://localhost:3000` | Main application |
| `http://localhost:3000/register` | Create a new account |
| `http://localhost:3000/login` | Sign in |
| `http://localhost:3000/privacy` | Privacy Policy (public) |
| `http://localhost:8001/api/health` | Backend health check |
| `http://localhost:8001/docs` | FastAPI interactive API docs (Swagger UI) |

---

## Deployment (Render)

A `render.yaml` is included for one-click deployment on [Render.com](https://render.com).

### Steps

1. Push this repository to GitHub
2. Create a new **Blueprint** on Render, pointing to this repo
3. Render will automatically detect `render.yaml` and create the service
4. In the Render dashboard, set the following environment variables:

   | Variable | Value |
   |---|---|
   | `SUPABASE_URL` | Your Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | Your Supabase service role key |
   | `APP_URL` | Your Render service URL (e.g. `https://realtouchhr.onrender.com`) |
   | `PUBLIC_APP_URL` | Same as above |
   | `REACT_APP_BACKEND_URL` | Same as above |
   | `GOOGLE_REDIRECT_URI` | `https://your-render-url.onrender.com/api/auth/google/callback` |
   | `PLATFORM_ADMINS` | Your email address |
   | All other keys | As required |

5. Update your **Google Cloud Console** OAuth app with the production redirect URI
6. Update your **Stripe** webhook endpoint to the production URL

The build command (`render.yaml`) installs frontend dependencies, builds the React app, and starts the FastAPI server which serves both the API and the static frontend build.

---

## Authentication

RealtouchHR supports three authentication methods:

### Email & Password
Standard registration at `/register`. Passwords are hashed with bcrypt. JWT tokens are issued on login and stored as HTTP-only cookies (with Bearer token fallback for API clients).

### Google OAuth
One-click sign in / sign up. Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REDIRECT_URI` to be set, and the redirect URI to be registered in [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials.

### Sandbox (Demo)
A public endpoint creates a temporary account pre-seeded with 6 demo employees, a pay run, UKVI alerts and more. Sandbox accounts expire after 24 hours.

### Two-Factor Authentication (2FA)
Users can enable TOTP-based 2FA from **Settings → Security**. A QR code is generated for Google Authenticator / Authy. Once enabled, every login requires a 6-digit code.

### Session management
Sessions are tracked in the database. Users can view and revoke active sessions. Admins can configure session timeout, max concurrent sessions and login lockout thresholds from the Super Admin panel.

---

## Platform / Super Admin

The Super Admin panel is accessible at `/super-admin` and is restricted to users whose email is listed in `PLATFORM_ADMINS` (env var) or who have `is_platform_admin: true` in their user record.

**There is no separate super admin account** — log in with your normal email/password (the one listed in `PLATFORM_ADMINS`) and you will automatically have access.

### Super Admin capabilities

| Tab | What you can do |
|---|---|
| **Companies** | View all tenants, suspend/restore, set plans, extend trials, delete, view detail |
| **Users** | View all users across all companies, disable/enable accounts |
| **Operators** | Add/remove platform staff with roles (owner, admin, support, billing, readonly) |
| **Feature Flags** | Toggle platform-wide features on/off |
| **Plans** | Create and manage subscription plan definitions |
| **Emergency** | RTI freeze, kill switches, emergency controls |
| **Audit Log** | Full platform-level audit trail |
| **Security** | MFA enforcement, session timeout, login lockout policies |
| **System Health** | Live API/DB health status |
| **Discount Codes** | View all promo code redemptions and usage stats |
| **Welcome Email** | Edit the welcome email template sent to every new signup, preview it, send a test |

---

## Key Modules

### Employees
- 8-step Add Employee wizard (Personal → Contact → Employment → Payroll → Bank → Right to Work → Emergency Contact → Review)
- Profile photo upload (base64, during wizard or on profile)
- Line manager assignment (builds the org chart hierarchy)
- Employment tab: job title, department, contract type, working pattern, probation, notice period, **line manager**
- Payroll tab: salary, tax code, NI category, pension, starter declaration
- Bank tab (masked for non-payroll roles)
- RTW tab: document type, expiry, follow-up, sponsored worker fields

### Org Chart
Located under **HR Analytics → Org Chart**.
- **List view**: indented hierarchy with avatars
- **Tree view**: visual organogram with department-coloured circular avatars and T-connector lines
- Hierarchy is data-driven from `line_manager_id` on each employee record
- Set line managers via **Employee Profile → Employment tab → Line Manager**

### Payroll & RTI
- Create pay runs for any period
- Per-employee payslips with tax/NI/pension calculations
- Export payslips as PDF
- RTI FPS (Full Payment Submission) and EPS (Employer Payment Summary) to HMRC
- Sandbox mode by default — set `RTI_LIVE_SUBMISSION_ENABLED=true` and provide HMRC Gateway credentials for live submissions

### UKVI & Immigration
- Track visa types, expiry dates and sponsored worker status per employee
- Sponsor licence management with renewal alerts
- Home Office reporting obligations flagged automatically
- Alerts integrated into the 180-day compliance calendar

### GDPR / DPO Centre
- Data subject request handling (access, erasure, portability, rectification)
- Configurable data retention policies (payroll: 7 years; RTW docs: 2 years)
- Breach log
- ICO-ready audit trail
- UK GDPR-compliant Privacy Policy at `/privacy` (publicly accessible)

### AI HR Copilot
Powered by Anthropic Claude. Accessible via the purple button in the bottom-left sidebar. Answers any HR, payroll or compliance question in the context of UK employment law.

### Billing
Stripe-powered. Three plans:
- **Starter** — £29/month
- **Professional** — £39/month
- **Enterprise** — £129/month

Promo codes can be applied at signup (see [Discount Codes](#discount--promo-codes)).

---

## API Overview

The FastAPI backend exposes all routes under `/api`. Interactive documentation is at `http://localhost:8001/docs`.

### Core endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/logout` | Logout |
| `GET` | `/api/auth/google` | Initiate Google OAuth |
| `GET` | `/api/auth/google/callback` | Google OAuth callback |
| `GET` | `/api/employees` | List employees |
| `POST` | `/api/employees` | Add employee |
| `GET` | `/api/employees/{id}` | Get employee |
| `PUT` | `/api/employees/{id}` | Update employee |
| `GET` | `/api/org-chart` | Organisation chart tree |
| `GET` | `/api/payroll/runs` | List pay runs |
| `POST` | `/api/payroll/runs` | Create pay run |
| `GET` | `/api/leave` | List leave requests |
| `POST` | `/api/leave` | Submit leave request |
| `GET` | `/api/compliance-calendar` | 180-day compliance events |
| `GET` | `/api/hr-reports/summary` | HR analytics summary |
| `GET` | `/api/company-lookup/search` | Companies House search (public) |
| `GET` | `/api/company-lookup/profile/{number}` | Companies House profile (public) |
| `GET` | `/api/discount-codes/validate` | Validate promo code (public) |
| `GET` | `/api/super-admin/metrics` | Platform metrics (admin only) |

---

## Email System

Emails are sent via [Resend](https://resend.com). Set `RESEND_API_KEY` in `.env` to enable. Without it, the email service runs in **mock mode** — emails are logged but not sent.

### Emails sent automatically

| Trigger | Email |
|---|---|
| New user registration | Rich welcome email with platform guide |
| Leave request approved/rejected | Notification to employee |
| Payslip available | Notification with net pay amount |
| Pension auto-enrolment | Statutory enrolment confirmation |
| Visa expiry approaching | Alert to HR manager |
| Timesheet approved/rejected | Notification to employee |

### Editing the welcome email

The welcome email template is fully editable by the platform owner without code changes:

1. Log in as Super Admin
2. Navigate to **Super Admin → Welcome Email**
3. Edit subject, from name, from email, and full HTML body
4. Use `{{name}}` and `{{company_name}}` as placeholders — they are substituted at send time
5. Click **Preview** to see a live rendered preview
6. Click **Send Test to My Email** to receive a real copy
7. Click **Save Template** — all future signups immediately receive the updated email

---

## Demo & Sandbox

### Live demo (no signup)

The landing page "Try the live demo" button creates a temporary sandbox account in seconds:
- 6 sample employees with a realistic org chart hierarchy
- A draft pay run
- UKVI alerts and compliance events
- Audit log entries
- Expires after 24 hours

### Seeding demo data into an existing account

From within the app (any account), navigate to the demo tour and click **Seed Demo Data**. This is idempotent — safe to run multiple times. It will:
- Create/update the 6 demo employees
- Wire up the org chart hierarchy (Olivia Williams at the top, others reporting through the tree)
- Create a sample pay run and payslips

---

## Discount / Promo Codes

A promotional discount system is built in. The default code is configured in `server.py` under `PROMO_CODES`.

**Current active code**: `BGS2026-` — 15% off all plans for 6 months.

### How it works

1. User enters a code in the **Discount Code** field on the signup page
2. The system validates it against `/api/discount-codes/validate`
3. On successful registration, the discount is recorded against the company and a usage record is saved
4. Super Admins can view all redemptions under **Super Admin → Discount Codes**

### Adding new codes

Edit `PROMO_CODES` in `backend/server.py`:

```python
PROMO_CODES: dict = {
    "YOURNEWCODE": {
        "code": "YOURNEWCODE",
        "display": "YOURNEWCODE-",
        "discount_percent": 20,
        "months": 3,
        "plans": "all",
        "description": "20% off all plans for 3 months",
        "active": True,
    }
}
```

---

## Companies House Integration

At registration, users can search for their company by name or registration number. The system queries the [Companies House REST API](https://developer.company-information.service.gov.uk) in real time and auto-fills verified company details.

### Setup

1. Register at the Companies House Developer Hub
2. Create an API key (REST API, not Streaming or OAuth)
3. Add to `backend/.env`:

```
COMPANIES_HOUSE_API_KEY=your-key-here
```

### What it does

- Debounced live search as the user types (450ms delay)
- Direct lookup if the input matches a company number format
- Displays company status (active = green, dissolved = amber with warning)
- On selection, saves a verified snapshot to the company record in the database
- Inactive company statuses (dissolved, liquidation, administration, etc.) trigger a warning — the user can still proceed

---

## Security

- **Passwords**: bcrypt hashed, never stored in plain text
- **JWT**: Short-lived tokens signed with `JWT_SECRET`, rotated on logout
- **Sessions**: Server-side session tracking, revocable per device
- **HTTPS**: Enforced in production (Render provides TLS automatically)
- **Rate limiting**: Login, registration and sensitive endpoints are rate-limited (SlowAPI)
- **Role-based access**: `owner`, `admin`, `hr_manager`, `payroll_admin`, `employee`, `platform_admin`
- **Bank details masking**: Bank account and sort code are masked in the UI for non-payroll roles
- **2FA**: TOTP-based two-factor authentication
- **GDPR**: Data retention policies, DSR handling, audit trails
- **Environment secrets**: All credentials in `.env` — never committed to source control
- **Companies House API key**: Backend-only, never exposed to the frontend

---

## Licence

Proprietary — © 2026 RealtouchHR Ltd. All rights reserved.
