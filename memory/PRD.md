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
3. **Payroll Admin** - Runs payroll, manages pay runs
4. **Manager** - Approves leave, views team schedules
5. **Employee** - Views payslips, requests leave
6. **Auditor** - Reviews audit logs, compliance reports

## Core Requirements (Static)
- JWT + Google OAuth authentication
- Employee management with compliance scoring
- Leave/absence management with calendar
- Document management with templates
- Time & scheduling (shifts, clock-in/out)
- UK payroll preview (pay runs, payslips, PAYE/NI calculations)
- Immutable audit log
- AI Copilot with human-in-the-loop
- Light/dark mode with user preference

## What's Been Implemented

### Stage 1 MVP - Complete (December 27, 2025)
- ✅ Authentication (JWT + Google OAuth via Emergent)
- ✅ Dashboard with Compliance Score and Next Best Action
- ✅ Employee Management (CRUD, compliance scoring)
- ✅ Leave Management (requests, approvals, calendar)
- ✅ Document Management (create, templates)
- ✅ Time & Scheduling (shifts, clock-in/out)
- ✅ Payroll Hub (guided flow, pay runs, payslips preview)
- ✅ Audit Log (immutable timeline)
- ✅ Settings (company, compliance tasks, theme)
- ✅ AI Copilot sidebar (GPT-4o integration)
- ✅ Light/Dark mode toggle

### Phase 2 Features - Complete (December 27, 2025)
- ✅ Employee Detail Page with edit functionality
- ✅ CSV Bulk Import (employees and timesheets)
- ✅ PDF Payslip Generation (individual downloads)
- ✅ HMRC Export Pack (FPS, EPS, P32 CSV exports)
- ✅ Leave Approval Notifications
- ✅ In-app Notifications System
- ✅ Time-to-First-Payroll Onboarding Wizard

### Backend APIs
- /api/auth/* - Authentication routes
- /api/company - Company management
- /api/employees - Employee CRUD
- /api/employees/import - CSV bulk import
- /api/employees/import/template - Download CSV template
- /api/leave - Leave management
- /api/documents - Document management
- /api/shifts - Shift/rota management
- /api/timesheets - Timesheet management
- /api/timesheets/import - CSV bulk import
- /api/payroll/runs - Payroll runs
- /api/payroll/runs/:id/payslips/:empId/pdf - PDF payslip download
- /api/payroll/runs/:id/export/fps - FPS export
- /api/payroll/runs/:id/export/eps - EPS export
- /api/payroll/runs/:id/export/p32 - P32 report
- /api/audit - Audit log
- /api/compliance/* - Compliance tasks and score
- /api/copilot/chat - AI Copilot
- /api/notifications - Notifications
- /api/onboarding/* - Onboarding wizard

### Frontend Pages
- /login, /register - Authentication
- /onboarding - Onboarding wizard
- /dashboard - Main dashboard
- /employees - Employee list
- /employees/:id - Employee detail & edit
- /leave - Leave management
- /documents - Documents
- /scheduling - Shifts & rotas
- /payroll - Payroll hub
- /payroll/:id - Pay run detail with exports
- /import - Bulk import
- /audit - Audit log
- /settings - Settings

### Tech Stack
- Backend: FastAPI + MongoDB (motor async) + reportlab (PDF)
- Frontend: React + Shadcn UI + Tailwind CSS
- Auth: JWT + Emergent Google OAuth
- AI: OpenAI GPT-4o (via Emergent LLM key)

## Prioritized Backlog

### P0 - Critical (Stage 2 - HMRC Integration)
- [ ] HMRC RTI API submission (FPS/EPS)
- [ ] Real-time validation against HMRC rules
- [ ] Tax code verification

### P1 - High Priority
- [ ] Full employee self-service portal
- [ ] Multi-entity/company support
- [ ] SCIM/SAML SSO integration
- [ ] Advanced RBAC with custom roles
- [ ] Working time directive checks

### P2 - Medium Priority
- [ ] Mobile responsive optimizations
- [ ] Email notifications (SendGrid/Resend)
- [ ] Holiday calendar integration
- [ ] Pension auto-enrollment workflow
- [ ] Student loan deductions

## Next Tasks
1. HMRC RTI API integration for live submission
2. Email notifications via SendGrid
3. Employee self-service dashboard
4. Multi-currency support
5. Advanced reporting & analytics
