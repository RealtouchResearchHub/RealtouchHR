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

## What's Been Implemented (December 27, 2025)

### Stage 1 MVP - Complete
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
- ✅ UK payroll calculations (PAYE, NI, pension)

### Backend APIs
- /api/auth/* - Authentication routes
- /api/company - Company management
- /api/employees - Employee CRUD
- /api/leave - Leave management
- /api/documents - Document management
- /api/shifts - Shift/rota management
- /api/timesheets - Timesheet management
- /api/payroll/runs - Payroll runs
- /api/audit - Audit log
- /api/compliance/* - Compliance tasks and score
- /api/copilot/chat - AI Copilot

### Tech Stack
- Backend: FastAPI + MongoDB (motor async)
- Frontend: React + Shadcn UI + Tailwind CSS
- Auth: JWT + Emergent Google OAuth
- AI: OpenAI GPT-4o (via Emergent LLM key)

## Prioritized Backlog

### P0 - Critical (Stage 2)
- [ ] HMRC RTI submission integration
- [ ] Full employee self-service portal
- [ ] Bulk employee import from CSV
- [ ] Pay element configuration (allowances, deductions)

### P1 - High Priority
- [ ] Multi-entity/company support
- [ ] SCIM/SAML SSO integration
- [ ] Advanced RBAC with custom roles
- [ ] Overtime rules engine
- [ ] Working time directive checks

### P2 - Medium Priority
- [ ] Mobile responsive improvements
- [ ] Email notifications
- [ ] PDF payslip generation
- [ ] Evidence locker exports
- [ ] Holiday calendar integration

## Next Tasks
1. Implement employee profile detail view
2. Add bulk payroll import from CSV
3. Implement PDF payslip generation
4. Add email notifications for approvals
5. HMRC export pack generation
