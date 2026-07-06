-- =============================================================================
-- RealtouchHR — Supabase (PostgreSQL) schema
-- Run this in the Supabase SQL Editor (Project → SQL Editor → New query)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
create table if not exists users (
    user_id                 text primary key,
    email                   text unique not null,
    name                    text,
    picture                 text,
    password_hash           text,
    role                    text default 'owner',
    company_id              text,
    employee_id             text,
    is_platform_admin       boolean default false,
    theme_preference        text default 'light',
    totp_secret             text,
    totp_enabled            boolean default false,
    backup_codes            jsonb default '[]',
    failed_logins           int default 0,
    locked_until            timestamptz,
    last_login              timestamptz,
    password_reset_token    text,
    password_reset_expires  timestamptz,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);
create index if not exists users_company_id_idx on users(company_id);
create index if not exists users_email_idx on users(email);

-- ---------------------------------------------------------------------------
-- password_reset_tokens
-- ---------------------------------------------------------------------------
create table if not exists password_reset_tokens (
    id          bigserial primary key,
    email       text not null unique,
    token       text not null,
    expires_at  text not null,
    used        boolean default false,
    created_at  timestamptz default now()
);
create index if not exists prt_token_idx on password_reset_tokens(token);

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------
create table if not exists companies (
    company_id              text primary key,
    name                    text,
    sector                  text,
    size                    text,
    address                 text,
    phone                   text,
    email                   text,
    website                 text,
    tax_reference           text,
    paye_reference          text,
    hmrc_sender_id          text,
    accounts_office_ref     text,
    owner_id                text,
    subscription_plan       text default 'free',
    subscription_name       text,
    subscription_status     text default 'inactive',
    subscription_active     boolean default false,
    subscription_updated_at timestamptz,
    employee_limit          int default 10,
    stripe_customer_id      text,
    stripe_subscription_id  text,
    bulk_downloads_active_until timestamptz,
    trust_badge_enabled     boolean default false,
    trust_badge_verified    boolean default false,
    compliance_score        int,
    currency                text default 'GBP',
    payroll_frequency       text default 'monthly',
    tax_year_start          text,
    suspended               boolean default false,
    suspended_reason        text,
    suspended_at            timestamptz,
    setup_completed         boolean default false,
    is_parent               boolean default false,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_sessions
-- ---------------------------------------------------------------------------
create table if not exists user_sessions (
    session_token   text primary key,
    user_id         text not null,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create index if not exists user_sessions_user_id_idx on user_sessions(user_id);

-- ---------------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------------
create table if not exists employees (
    employee_id             text primary key,
    company_id              text not null,
    user_id                 text,
    first_name              text,
    last_name               text,
    preferred_name          text,
    email                   text,
    work_email              text,
    phone                   text,
    mobile_phone            text,
    job_title               text,
    department              text,
    work_location           text,
    line_manager_id         text,
    start_date              text,
    end_date                text,
    probation_end_date      text,
    notice_period           text,
    reason_for_leaving      text,
    employment_type         text default 'full_time',
    contract_type           text,
    status                  text default 'active',
    salary                  numeric,
    pay_frequency           text default 'monthly',
    salary_type             text default 'annual',
    currency                text default 'GBP',
    payroll_id              text,
    payroll_status          text default 'active',
    payroll_start_date      text,
    starter_declaration     text,
    ni_number               text,
    ni_category             text default 'A',
    tax_code                text,
    student_loan            text,
    postgraduate_loan       boolean default false,
    pension_enrolled        boolean default false,
    auto_enrolment_status   text,
    director_payroll        boolean default false,
    date_of_birth           text,
    gender                  text,
    nationality             text,
    address                 jsonb default '{}',
    bank_name               text,
    bank_sort_code          text,
    bank_account            text,
    bank_account_holder     text,
    payment_method          text default 'bacs',
    -- Right to Work
    right_to_work_status    text,
    rtw_check_date          text,
    rtw_expiry_date         text,
    rtw_followup_date       text,
    rtw_document_type       text,
    right_to_work           text,
    -- UKVI / Sponsorship
    is_sponsored_worker     boolean default false,
    cos_number              text,
    soc_code                text,
    visa_type               text,
    visa_expiry_date        text,
    visa_expiry             text,
    cos_salary              numeric,
    cos_job_title           text,
    cos_work_location       text,
    sponsorship_start_date  text,
    sponsorship_end_date    text,
    -- Readiness flags (denormalized for fast queries)
    payroll_ready           boolean default false,
    rti_ready               boolean default false,
    right_to_work_ready     boolean default false,
    hr_profile_ready        boolean default false,
    ukvi_ready              boolean default false,
    documents_ready         boolean default false,
    -- Other
    emergency_contact       jsonb default '{}',
    custom_fields           jsonb default '{}',
    picture                 text,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);
create index if not exists employees_company_id_idx on employees(company_id);
create index if not exists employees_email_idx on employees(email);
create index if not exists employees_status_idx on employees(status);

-- ---------------------------------------------------------------------------
-- pay_runs
-- ---------------------------------------------------------------------------
create table if not exists pay_runs (
    payrun_id       text primary key,
    company_id      text not null,
    tax_year        text,
    tax_period      int,
    period_start    text,
    period_end      text,
    pay_date        text,
    status          text default 'draft',
    total_gross     numeric default 0,
    total_net       numeric default 0,
    total_tax       numeric default 0,
    total_ni        numeric default 0,
    employee_count  int default 0,
    rti_submitted   boolean default false,
    rti_submitted_at timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists pay_runs_company_id_idx on pay_runs(company_id);

-- ---------------------------------------------------------------------------
-- payslips
-- ---------------------------------------------------------------------------
create table if not exists payslips (
    payslip_id          text primary key,
    payrun_id           text,
    company_id          text not null,
    employee_id         text,
    employee_name       text,
    employee_email      text,
    tax_year            text,
    tax_period          int,
    pay_date            text,
    gross_pay           numeric default 0,
    net_pay             numeric default 0,
    income_tax          numeric default 0,
    national_insurance  numeric default 0,
    pension_ee          numeric default 0,
    pension_er          numeric default 0,
    student_loan        numeric default 0,
    earnings            jsonb default '[]',
    deductions          jsonb default '[]',
    ytd                 jsonb default '{}',
    status              text default 'draft',
    created_at          timestamptz default now()
);
create index if not exists payslips_payrun_id_idx on payslips(payrun_id);
create index if not exists payslips_company_id_idx on payslips(company_id);
create index if not exists payslips_employee_id_idx on payslips(employee_id);

-- ---------------------------------------------------------------------------
-- payment_transactions
-- ---------------------------------------------------------------------------
create table if not exists payment_transactions (
    transaction_id      text primary key,
    session_id          text,
    company_id          text,
    user_id             text,
    user_email          text,
    type                text,
    plan_id             text,
    plan_name           text,
    addon_id            text,
    addon_name          text,
    payslip_id          text,
    payrun_id           text,
    amount              numeric,
    amount_total        numeric,
    currency            text default 'gbp',
    quantity            int default 1,
    payment_status      text default 'pending',
    status              text default 'initiated',
    stripe_customer_id  text,
    payment_intent_id   text,
    receipt_url         text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists payment_transactions_company_id_idx on payment_transactions(company_id);
create index if not exists payment_transactions_session_id_idx on payment_transactions(session_id);

-- ---------------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------------
create table if not exists audit_log (
    audit_id        text primary key default gen_random_uuid()::text,
    company_id      text,
    user_id         text,
    action          text,
    entity_type     text,
    entity_id       text,
    details         jsonb default '{}',
    ip_address      text,
    timestamp       timestamptz default now()
);
create index if not exists audit_log_company_id_idx on audit_log(company_id);
create index if not exists audit_log_timestamp_idx on audit_log(timestamp);

-- ---------------------------------------------------------------------------
-- leave_requests
-- ---------------------------------------------------------------------------
create table if not exists leave_requests (
    leave_request_id    text primary key,
    leave_id            text,
    company_id          text not null,
    employee_id         text,
    employee_name       text,
    leave_type          text,
    start_date          text,
    end_date            text,
    days                numeric,
    status              text default 'pending',
    reason              text,
    approved_by         text,
    approved_at         timestamptz,
    rejected_reason     text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists leave_requests_company_id_idx on leave_requests(company_id);
create index if not exists leave_requests_employee_id_idx on leave_requests(employee_id);

-- ---------------------------------------------------------------------------
-- leave_balances
-- ---------------------------------------------------------------------------
create table if not exists leave_balances (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    leave_type      text,
    year            int,
    entitlement     numeric default 0,
    used            numeric default 0,
    pending         numeric default 0,
    carried_over    numeric default 0,
    updated_at      timestamptz default now()
);
create index if not exists leave_balances_employee_id_idx on leave_balances(employee_id);

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
create table if not exists documents (
    document_id     text primary key,
    company_id      text not null,
    employee_id     text,
    uploaded_by     text,
    created_by      text,
    name            text,
    type            text,
    doc_type        text,
    category        text,
    content         text,
    file_url        text,
    file_size       int,
    mime_type       text,
    description     text,
    status          text default 'draft',
    tags            jsonb default '[]',
    expires_at      timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists documents_company_id_idx on documents(company_id);
create index if not exists documents_employee_id_idx on documents(employee_id);

-- ---------------------------------------------------------------------------
-- secure_documents
-- ---------------------------------------------------------------------------
create table if not exists secure_documents (
    document_id     text primary key,
    company_id      text,
    employee_id     text,
    name            text,
    type            text,
    content         text,
    metadata        jsonb default '{}',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- policies
-- ---------------------------------------------------------------------------
create table if not exists policies (
    policy_id       text primary key,
    company_id      text not null,
    title           text,
    category        text,
    content         text,
    version         text,
    status          text default 'draft',
    requires_acknowledgement boolean default false,
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists policies_company_id_idx on policies(company_id);

-- ---------------------------------------------------------------------------
-- policy_versions
-- ---------------------------------------------------------------------------
create table if not exists policy_versions (
    record_id       text primary key,
    policy_id       text,
    company_id      text,
    version         text,
    content         text,
    created_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- policy_acknowledgements
-- ---------------------------------------------------------------------------
create table if not exists policy_acknowledgements (
    record_id       text primary key,
    policy_id       text,
    company_id      text,
    employee_id     text,
    employee_name   text,
    version         text,
    acknowledged_at timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- training_courses
-- ---------------------------------------------------------------------------
create table if not exists training_courses (
    training_id     text primary key,
    company_id      text not null,
    title           text,
    description     text,
    category        text,
    duration_hours  numeric,
    mandatory       boolean default false,
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- training_records
-- ---------------------------------------------------------------------------
create table if not exists training_records (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    training_id     text,
    course_name     text,
    status          text default 'enrolled',
    score           numeric,
    completed_at    timestamptz,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create index if not exists training_records_employee_id_idx on training_records(employee_id);

-- ---------------------------------------------------------------------------
-- performance_appraisals
-- ---------------------------------------------------------------------------
create table if not exists performance_appraisals (
    review_id       text primary key,
    company_id      text,
    employee_id     text,
    reviewer_id     text,
    period          text,
    status          text default 'draft',
    overall_rating  numeric,
    goals           jsonb default '[]',
    feedback        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- appraisals (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists appraisals (
    review_id       text primary key,
    company_id      text,
    employee_id     text,
    reviewer_id     text,
    period          text,
    status          text default 'draft',
    overall_rating  numeric,
    goals           jsonb default '[]',
    feedback        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- objectives
-- ---------------------------------------------------------------------------
create table if not exists objectives (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    title           text,
    description     text,
    status          text default 'active',
    progress        int default 0,
    due_date        text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- performance_notes
-- ---------------------------------------------------------------------------
create table if not exists performance_notes (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    author_id       text,
    note            text,
    type            text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- review_notes (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists review_notes (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    author_id       text,
    note            text,
    type            text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- absence_records
-- ---------------------------------------------------------------------------
create table if not exists absence_records (
    absence_id      text primary key,
    company_id      text not null,
    employee_id     text,
    type            text,
    start_date      text,
    end_date        text,
    days            numeric,
    reason          text,
    fit_note        boolean default false,
    status          text default 'open',
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists absence_records_company_id_idx on absence_records(company_id);

-- ---------------------------------------------------------------------------
-- rtw_checks
-- ---------------------------------------------------------------------------
create table if not exists rtw_checks (
    rtw_id          text primary key,
    company_id      text,
    employee_id     text,
    document_type   text,
    document_number text,
    expiry_date     text,
    verified        boolean default false,
    verified_by     text,
    verified_at     timestamptz,
    status          text default 'pending',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists rtw_checks_employee_id_idx on rtw_checks(employee_id);

-- ---------------------------------------------------------------------------
-- certificates_of_sponsorship
-- ---------------------------------------------------------------------------
create table if not exists certificates_of_sponsorship (
    cos_id          text primary key,
    company_id      text,
    employee_id     text,
    cos_number      text,
    visa_type       text,
    start_date      text,
    expiry_date     text,
    status          text default 'active',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- cos_register (alias table same structure)
-- ---------------------------------------------------------------------------
create table if not exists cos_register (
    cos_id          text primary key,
    company_id      text,
    employee_id     text,
    cos_number      text,
    visa_type       text,
    start_date      text,
    expiry_date     text,
    status          text default 'active',
    notes           text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- ukvi_alerts / ukvi_reports / ukvi_reporting_events
-- ---------------------------------------------------------------------------
create table if not exists ukvi_alerts (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    alert_type      text,
    severity        text,
    message         text,
    status          text default 'open',
    created_at      timestamptz default now()
);
create table if not exists ukvi_reports (
    record_id       text primary key,
    company_id      text,
    report_type     text,
    period          text,
    data            jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists ukvi_reporting_events (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    event_type      text,
    event_date      text,
    details         jsonb default '{}',
    submitted       boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- pension_schemes / pension_enrolments
-- ---------------------------------------------------------------------------
create table if not exists pension_schemes (
    record_id       text primary key,
    company_id      text,
    provider        text,
    scheme_name     text,
    employer_rate   numeric,
    employee_rate   numeric,
    status          text default 'active',
    created_at      timestamptz default now()
);
create table if not exists pension_enrolments (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    scheme_id       text,
    enrolment_date  text,
    opt_out_date    text,
    status          text default 'enrolled',
    employee_rate   numeric,
    employer_rate   numeric,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- statutory_payments
-- ---------------------------------------------------------------------------
create table if not exists statutory_payments (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    type            text,
    start_date      text,
    end_date        text,
    weekly_rate     numeric,
    total_amount    numeric,
    status          text default 'active',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- tax_documents
-- ---------------------------------------------------------------------------
create table if not exists tax_documents (
    tax_doc_id      text primary key,
    company_id      text,
    employee_id     text,
    type            text,
    tax_year        text,
    content         jsonb default '{}',
    pdf_url         text,
    status          text default 'draft',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- timesheets / clock_events / shifts / rotas
-- ---------------------------------------------------------------------------
create table if not exists timesheets (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    date            text,
    start_time      text,
    end_time        text,
    break_minutes   int default 0,
    hours_worked    numeric,
    type            text default 'regular',
    status          text default 'pending',
    notes           text,
    created_at      timestamptz default now()
);
create table if not exists clock_events (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    event_type      text,
    timestamp       timestamptz default now(),
    location        text,
    device          text
);
create table if not exists shifts (
    entry_id        text primary key,
    company_id      text,
    employee_id     text,
    date            text,
    start_time      text,
    end_time        text,
    role            text,
    department      text,
    status          text default 'scheduled',
    created_at      timestamptz default now()
);
create table if not exists rotas (
    record_id       text primary key,
    company_id      text,
    week_start      text,
    shifts          jsonb default '[]',
    created_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- er_cases
-- ---------------------------------------------------------------------------
create table if not exists er_cases (
    case_id         text primary key,
    case_number     text,
    company_id      text,
    employee_id     text,
    case_type       text,
    title           text,
    description     text,
    severity        text,
    incident_date   text,
    raised_by       text,
    confidential    boolean default true,
    status          text default 'open',
    outcome         text,
    hearing_date    text,
    notes           text,
    events          jsonb default '[]',
    documents       jsonb default '[]',
    assigned_to     text,
    resolution      text,
    created_by      text,
    created_by_name text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- GDPR tables
-- ---------------------------------------------------------------------------
create table if not exists data_processing_activities (
    record_id       text primary key,
    company_id      text,
    name            text,
    purpose         text,
    lawful_basis    text,
    data_categories jsonb default '[]',
    retention_period text,
    status          text default 'active',
    created_at      timestamptz default now()
);
create table if not exists dsar_requests (
    record_id       text primary key,
    company_id      text,
    subject_name    text,
    subject_email   text,
    request_type    text,
    status          text default 'pending',
    due_date        text,
    response        text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create table if not exists dpia_records (
    record_id       text primary key,
    company_id      text,
    title           text,
    description     text,
    risk_level      text,
    status          text default 'draft',
    created_at      timestamptz default now()
);
create table if not exists gdpr_erasure_requests (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    requested_by    text,
    status          text default 'pending',
    completed_at    timestamptz,
    created_at      timestamptz default now()
);
create table if not exists breach_incidents (
    record_id       text primary key,
    company_id      text,
    title           text,
    description     text,
    severity        text,
    reported_to_ico boolean default false,
    status          text default 'open',
    created_at      timestamptz default now()
);
create table if not exists processors_register (
    record_id       text primary key,
    company_id      text,
    processor_name  text,
    services        text,
    dpa_in_place    boolean default false,
    created_at      timestamptz default now()
);
create table if not exists retention_overrides (
    record_id       text primary key,
    company_id      text,
    data_type       text,
    retention_days  int,
    reason          text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- salary_history
-- ---------------------------------------------------------------------------
create table if not exists salary_history (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    salary          numeric,
    currency        text default 'GBP',
    effective_date  text,
    reason          text,
    changed_by      text,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- notifications
-- ---------------------------------------------------------------------------
create table if not exists notifications (
    record_id       text primary key,
    user_id         text,
    company_id      text,
    type            text,
    title           text,
    message         text,
    read            boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_2fa
-- ---------------------------------------------------------------------------
create table if not exists user_2fa (
    record_id       text primary key,
    user_id         text,
    code            text,
    type            text,
    expires_at      timestamptz,
    used            boolean default false,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- user_invites
-- ---------------------------------------------------------------------------
create table if not exists user_invites (
    invite_token    text primary key,
    company_id      text,
    invited_by      text,
    email           text,
    role            text default 'employee',
    status          text default 'pending',
    expires_at      timestamptz,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- RTI submission tables
-- ---------------------------------------------------------------------------
create table if not exists rti_submissions (
    record_id       text primary key,
    company_id      text,
    submission_type text,
    tax_year        text,
    tax_period      int,
    payrun_id       text,
    status          text default 'pending',
    response_code   text,
    response_message text,
    submitted_at    timestamptz,
    created_at      timestamptz default now()
);
create table if not exists rti_payloads (
    record_id       text primary key,
    company_id      text,
    submission_id   text,
    payload         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_receipts (
    record_id       text primary key,
    company_id      text,
    submission_id   text,
    receipt_data    jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_audit_ledger (
    record_id       text primary key,
    company_id      text,
    action          text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists rti_leaver_queue (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    payrun_id       text,
    processed       boolean default false,
    created_at      timestamptz default now()
);
create table if not exists eps_submissions (
    record_id       text primary key,
    company_id      text,
    tax_year        text,
    tax_period      int,
    status          text default 'pending',
    created_at      timestamptz default now()
);
create table if not exists p60_queue (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    tax_year        text,
    status          text default 'pending',
    created_at      timestamptz default now()
);
create table if not exists p11d_records (
    record_id       text primary key,
    company_id      text,
    employee_id     text,
    tax_year        text,
    benefits        jsonb default '[]',
    total_value     numeric default 0,
    status          text default 'draft',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- compliance_tasks
-- ---------------------------------------------------------------------------
create table if not exists compliance_tasks (
    record_id       text primary key,
    company_id      text,
    title           text,
    category        text,
    status          text default 'pending',
    due_date        text,
    assigned_to     text,
    completed_at    timestamptz,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- download_passes / download_usage
-- ---------------------------------------------------------------------------
create table if not exists download_passes (
    pass_id         text primary key,
    company_id      text,
    user_id         text,
    resource_id     text,
    resource_type   text,
    transaction_id  text,
    used            boolean default false,
    expires_at      timestamptz,
    created_at      timestamptz default now()
);
create table if not exists download_usage (
    record_id       text primary key,
    company_id      text,
    user_id         text,
    resource_id     text,
    resource_type   text,
    month           text,
    count           int default 0,
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- feature_flags / platform_plans / sso_configs / roles / entities / organizations
-- ---------------------------------------------------------------------------
create table if not exists feature_flags (
    record_id       text primary key,
    company_id      text,
    flag_name       text,
    enabled         boolean default false,
    updated_at      timestamptz default now()
);
create table if not exists platform_plans (
    record_id       text primary key,
    plan_id         text unique,
    name            text,
    price           numeric,
    currency        text default 'gbp',
    features        jsonb default '[]',
    employee_limit  int,
    active          boolean default true,
    created_at      timestamptz default now()
);
create table if not exists sso_configs (
    record_id       text primary key,
    company_id      text unique,
    provider        text,
    metadata_url    text,
    entity_id       text,
    config          jsonb default '{}',
    enabled         boolean default false,
    created_at      timestamptz default now()
);
create table if not exists roles (
    record_id       text primary key,
    company_id      text,
    name            text,
    permissions     jsonb default '[]',
    created_at      timestamptz default now()
);
create table if not exists entities (
    record_id       text primary key,
    company_id      text,
    name            text,
    type            text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);
create table if not exists organizations (
    record_id       text primary key,
    company_id      text,
    name            text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);

-- ===========================================================================
-- UKVI COMPLIANCE SCANNER TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- ukvi_compliance_rules — static rules engine (seeded once)
-- ---------------------------------------------------------------------------
create table if not exists ukvi_compliance_rules (
    rule_id         text primary key,
    rule_code       text unique not null,
    category        text not null,
    title           text not null,
    description     text,
    severity        text default 'medium',
    check_type      text,
    enabled         boolean default true,
    created_at      timestamptz default now()
);
create index if not exists ukvi_compliance_rules_category_idx on ukvi_compliance_rules(category);

-- ---------------------------------------------------------------------------
-- ukvi_compliance_scans — one scan per invocation
-- ---------------------------------------------------------------------------
create table if not exists ukvi_compliance_scans (
    scan_id             text primary key,
    company_id          text not null,
    initiated_by        text,
    status              text default 'running',
    overall_score       int,
    risk_level          text,
    total_employees     int default 0,
    flagged_employees   int default 0,
    passed_checks       int default 0,
    failed_checks       int default 0,
    warning_checks      int default 0,
    summary             jsonb default '{}',
    completed_at        timestamptz,
    created_at          timestamptz default now()
);
create index if not exists ukvi_compliance_scans_company_id_idx on ukvi_compliance_scans(company_id);
create index if not exists ukvi_compliance_scans_created_at_idx on ukvi_compliance_scans(created_at);

-- ---------------------------------------------------------------------------
-- ukvi_compliance_scan_results — per-employee per-rule results
-- ---------------------------------------------------------------------------
create table if not exists ukvi_compliance_scan_results (
    result_id       text primary key,
    scan_id         text not null,
    company_id      text not null,
    employee_id     text,
    employee_name   text,
    rule_id         text,
    rule_code       text,
    category        text,
    status          text,
    severity        text,
    message         text,
    detail          jsonb default '{}',
    created_at      timestamptz default now()
);
create index if not exists ukvi_scan_results_scan_id_idx on ukvi_compliance_scan_results(scan_id);
create index if not exists ukvi_scan_results_company_id_idx on ukvi_compliance_scan_results(company_id);

-- ---------------------------------------------------------------------------
-- ukvi_scan_entitlements — quota: 2 scans per billing month per company
-- ---------------------------------------------------------------------------
create table if not exists ukvi_scan_entitlements (
    record_id               text primary key,
    company_id              text not null,
    billing_period_start    date not null,
    billing_period_end      date not null,
    scans_used              int default 0,
    scans_limit             int default 2,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);
create index if not exists ukvi_scan_entitlements_company_id_idx on ukvi_scan_entitlements(company_id);
create unique index if not exists ukvi_scan_entitlements_period_idx on ukvi_scan_entitlements(company_id, billing_period_start);

-- ---------------------------------------------------------------------------
-- ukvi_report_exports — PDF/DOCX report generation records
-- ---------------------------------------------------------------------------
create table if not exists ukvi_report_exports (
    export_id       text primary key,
    scan_id         text not null,
    company_id      text not null,
    format          text not null,
    file_url        text,
    generated_by    text,
    file_size       int,
    created_at      timestamptz default now()
);
create index if not exists ukvi_report_exports_scan_id_idx on ukvi_report_exports(scan_id);

-- ===========================================================================
-- EMPLOYEE LIFECYCLE & READINESS TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- employee_status_history — immutable lifecycle status changes
-- ---------------------------------------------------------------------------
create table if not exists employee_status_history (
    record_id       text primary key,
    company_id      text not null,
    employee_id     text not null,
    previous_status text,
    new_status      text not null,
    changed_by      text,
    reason          text,
    created_at      timestamptz default now()
);
create index if not exists emp_status_history_employee_id_idx on employee_status_history(employee_id);

-- ---------------------------------------------------------------------------
-- employee_readiness_checks — readiness flags per employee
-- ---------------------------------------------------------------------------
create table if not exists employee_readiness_checks (
    record_id               text primary key,
    company_id              text not null,
    employee_id             text not null unique,
    hr_profile_ready        boolean default false,
    payroll_ready           boolean default false,
    rti_ready               boolean default false,
    right_to_work_ready     boolean default false,
    ukvi_ready              boolean default false,
    documents_ready         boolean default false,
    readiness_issues        jsonb default '[]',
    last_checked_at         timestamptz default now(),
    updated_at              timestamptz default now()
);
create index if not exists emp_readiness_company_id_idx on employee_readiness_checks(company_id);

-- ===========================================================================
-- PLATFORM OPERATOR / SUPER ADMIN TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- platform_operators — super admin users with structured roles
-- ---------------------------------------------------------------------------
create table if not exists platform_operators (
    operator_id     text primary key,
    user_id         text unique not null,
    email           text not null,
    name            text,
    role            text default 'platform_support',
    is_active       boolean default true,
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists platform_operators_email_idx on platform_operators(email);

-- ---------------------------------------------------------------------------
-- platform_audit_logs — immutable platform-wide audit trail
-- ---------------------------------------------------------------------------
create table if not exists platform_audit_logs (
    log_id          text primary key,
    operator_id     text,
    operator_email  text,
    action          text not null,
    target_type     text,
    target_id       text,
    details         jsonb default '{}',
    ip_address      text,
    created_at      timestamptz default now()
);
create index if not exists platform_audit_logs_created_at_idx on platform_audit_logs(created_at);
create index if not exists platform_audit_logs_operator_id_idx on platform_audit_logs(operator_id);

-- ---------------------------------------------------------------------------
-- platform_feature_flags — global feature flags with plan/company overrides
-- ---------------------------------------------------------------------------
create table if not exists platform_feature_flags (
    flag_id             text primary key,
    flag_key            text unique not null,
    display_name        text,
    description         text,
    global_enabled      boolean default true,
    plan_rules_json     jsonb default '{}',
    company_overrides   jsonb default '{}',
    updated_by          text,
    updated_at          timestamptz default now(),
    created_at          timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- emergency_actions — audit log for kill switch / emergency controls
-- ---------------------------------------------------------------------------
create table if not exists emergency_actions (
    action_id       text primary key,
    operator_email  text not null,
    action_type     text not null,
    target_id       text,
    reason          text,
    reverted_at     timestamptz,
    reverted_by     text,
    details         jsonb default '{}',
    created_at      timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- support_access_sessions — impersonation audit trail
-- ---------------------------------------------------------------------------
create table if not exists support_access_sessions (
    session_id      text primary key,
    operator_email  text not null,
    target_user_id  text not null,
    target_email    text,
    company_id      text,
    reason          text,
    token           text,
    expires_at      timestamptz,
    ended_at        timestamptz,
    created_at      timestamptz default now()
);

-- ===========================================================================
-- HMRC RTI CONFIGURATION
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- hmrc_rti_config — per-company HMRC RTI credentials and mode
-- ---------------------------------------------------------------------------
create table if not exists hmrc_rti_config (
    config_id               text primary key,
    company_id              text unique not null,
    rti_mode                text default 'sandbox',
    gateway_user_id         text,
    gateway_password_hash   text,
    paye_reference          text,
    accounts_office_ref     text,
    employer_name           text,
    employer_address        jsonb default '{}',
    sender_id               text,
    software_name           text default 'RealtouchHR',
    sandbox_endpoint        text,
    production_endpoint     text,
    go_live_approved        boolean default false,
    go_live_approved_by     text,
    go_live_approved_at     timestamptz,
    readiness_checklist     jsonb default '{}',
    last_test_submission_at timestamptz,
    created_at              timestamptz default now(),
    updated_at              timestamptz default now()
);

-- ===========================================================================
-- FEATURE ENTITLEMENTS (per-company plan-based feature access)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- feature_entitlements — per-company feature gating
-- ---------------------------------------------------------------------------
create table if not exists feature_entitlements (
    record_id       text primary key,
    company_id      text not null,
    feature_key     text not null,
    enabled         boolean default true,
    source          text default 'plan',
    expires_at      timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create unique index if not exists feature_entitlements_unique_idx on feature_entitlements(company_id, feature_key);

-- ---------------------------------------------------------------------------
-- company_module_settings — module enable/disable per company
-- ---------------------------------------------------------------------------
create table if not exists company_module_settings (
    record_id       text primary key,
    company_id      text not null,
    module_key      text not null,
    enabled         boolean default true,
    config          jsonb default '{}',
    updated_by      text,
    updated_at      timestamptz default now()
);
create unique index if not exists company_module_settings_unique_idx on company_module_settings(company_id, module_key);

-- ---------------------------------------------------------------------------
-- user_permissions — fine-grained RBAC overrides per user
-- ---------------------------------------------------------------------------
create table if not exists user_permissions (
    record_id       text primary key,
    company_id      text not null,
    user_id         text not null,
    permission_key  text not null,
    granted         boolean default true,
    granted_by      text,
    created_at      timestamptz default now()
);
create unique index if not exists user_permissions_unique_idx on user_permissions(company_id, user_id, permission_key);

-- ===========================================================================
-- RECRUITMENT MODULE
-- ===========================================================================

create table if not exists recruitment_jobs (
    job_id          text primary key,
    company_id      text not null,
    title           text,
    department      text,
    location        text,
    contract_type   text,
    salary_min      numeric,
    salary_max      numeric,
    salary_range    text,
    closing_date    text,
    description     text,
    requirements    text,
    status          text default 'open',
    created_by      text,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists recruitment_jobs_company_id_idx on recruitment_jobs(company_id);
create index if not exists recruitment_jobs_status_idx on recruitment_jobs(status);

create table if not exists recruitment_applicants (
    applicant_id    text primary key,
    job_id          text,
    company_id      text not null,
    name            text,
    email           text,
    phone           text,
    cv_url          text,
    cover_letter    text,
    stage           text default 'applied',
    rating          int,
    notes           text,
    offer_sent      boolean default false,
    hired           boolean default false,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists recruitment_applicants_job_id_idx on recruitment_applicants(job_id);
create index if not exists recruitment_applicants_company_id_idx on recruitment_applicants(company_id);

-- ===========================================================================
-- EXPENSES MODULE
-- ===========================================================================

create table if not exists expense_claims (
    claim_id        text primary key,
    company_id      text not null,
    employee_id     text,
    employee_name   text,
    title           text,
    category        text,
    amount          numeric,
    currency        text default 'GBP',
    expense_date    text,
    description     text,
    receipt_url     text,
    status          text default 'pending',
    approved_by     text,
    approved_at     timestamptz,
    rejected_reason text,
    paid_at         timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists expense_claims_company_id_idx on expense_claims(company_id);
create index if not exists expense_claims_employee_id_idx on expense_claims(employee_id);
create index if not exists expense_claims_status_idx on expense_claims(status);

create table if not exists mileage_claims (
    claim_id        text primary key,
    company_id      text not null,
    employee_id     text,
    employee_name   text,
    journey_date    text,
    from_location   text,
    to_location     text,
    miles           numeric,
    vehicle_type    text default 'car',
    purpose         text,
    rate            numeric,
    amount          numeric,
    total_miles_ytd numeric default 0,
    status          text default 'pending',
    approved_by     text,
    approved_at     timestamptz,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);
create index if not exists mileage_claims_company_id_idx on mileage_claims(company_id);
create index if not exists mileage_claims_employee_id_idx on mileage_claims(employee_id);

-- ===========================================================================
-- SAFE ALTER TABLE migrations — add columns that may be missing from earlier
-- schema runs. These are all IF NOT EXISTS to be idempotent.
-- ===========================================================================

-- employees: wizard fields not in the original schema
alter table if exists employees add column if not exists title             text;
alter table if exists employees add column if not exists middle_name       text;
alter table if exists employees add column if not exists working_pattern   text;
alter table if exists employees add column if not exists hours_per_week    numeric;
alter table if exists employees add column if not exists avatar_url        text;

-- companies: logo storage
alter table if exists companies add column if not exists logo_url          text;

-- users: forced password change on first login for employee-created accounts
alter table if exists users add column if not exists must_change_password  boolean default false;

-- documents: columns used by the create-document route
alter table if exists documents add column if not exists doc_type    text;
alter table if exists documents add column if not exists created_by  text;
alter table if exists documents add column if not exists content     text;
alter table if exists documents add column if not exists status      text default 'draft';
alter table if exists documents add column if not exists updated_at  timestamptz default now();

-- er_cases: columns added after initial schema creation
alter table if exists er_cases add column if not exists case_number     text;
alter table if exists er_cases add column if not exists title            text;
alter table if exists er_cases add column if not exists severity         text;
alter table if exists er_cases add column if not exists incident_date    text;
alter table if exists er_cases add column if not exists raised_by        text;
alter table if exists er_cases add column if not exists confidential     boolean default true;
alter table if exists er_cases add column if not exists outcome          text;
alter table if exists er_cases add column if not exists hearing_date     text;
alter table if exists er_cases add column if not exists notes            text;
alter table if exists er_cases add column if not exists events           jsonb default '[]';
alter table if exists er_cases add column if not exists documents        jsonb default '[]';
alter table if exists er_cases add column if not exists created_by       text;
alter table if exists er_cases add column if not exists created_by_name  text;

-- RTI sandbox/live labeling — lets the app distinguish a sandbox simulation
-- from a real HMRC Gateway/embedded-provider submission, instead of relying
-- on the "submitted"/"accepted" status alone.
alter table if exists rti_submissions add column if not exists is_simulated        boolean default true;
alter table if exists rti_submissions add column if not exists submission_channel  text;
alter table if exists rti_submissions add column if not exists live_submission     boolean default false;
alter table if exists rti_receipts    add column if not exists is_simulated        boolean default true;

-- rti_submissions/rti_receipts: application code has always looked submissions up
-- by "submission_id" (the app-generated ID, e.g. "rti_xxxx"), but that column was
-- missing from the original schema (only the internal record_id PK existed) —
-- every lookup by submission_id crashed with "column does not exist". Backfilling
-- it here since it is required for both the legacy HMRC routes and the RTI Sync
-- engine's prepare/approve/submit/poll flow to function at all.
alter table if exists rti_submissions add column if not exists submission_id text;
create index if not exists rti_submissions_submission_id_idx on rti_submissions(submission_id);
create index if not exists rti_receipts_submission_id_idx on rti_receipts(submission_id);

-- pay_runs: sandbox-simulated RTI submission marker, separate from a real
-- rti_submitted flag (which must only ever be set by a live response).
alter table if exists pay_runs add column if not exists rti_submitted             boolean default false;
alter table if exists pay_runs add column if not exists rti_submission_simulated  boolean default false;
alter table if exists pay_runs add column if not exists rti_submission_id         text;
alter table if exists pay_runs add column if not exists rti_correlation_id        text;

-- pension_enrolments / employees: pension enrolment is recorded internally only
-- until a real pension provider / Pensions Regulator integration exists.
alter table if exists pension_enrolments add column if not exists enrolment_recorded_locally  boolean default true;
alter table if exists pension_enrolments add column if not exists provider_confirmed          boolean default false;
alter table if exists employees add column if not exists pension_enrolment_recorded_locally   boolean default true;
alter table if exists employees add column if not exists pension_provider_confirmed           boolean default false;

-- pension_schemes: application code has always used scheme_id (external ID) and
-- several metadata fields that were missing from the original schema — filtering
-- by scheme_id or is_default crashed with "column does not exist", meaning
-- get_default_scheme()/update_scheme() (and therefore the whole enrol_employee()
-- flow) could never actually run.
alter table if exists pension_schemes add column if not exists scheme_id          text;
alter table if exists pension_schemes add column if not exists is_default        boolean default false;
alter table if exists pension_schemes add column if not exists pension_type      text;
alter table if exists pension_schemes add column if not exists qualifying_basis  text;
alter table if exists pension_schemes add column if not exists employer_reference text;
alter table if exists pension_schemes add column if not exists staging_date      date;
create index if not exists pension_schemes_scheme_id_idx on pension_schemes(scheme_id);

-- pension_enrolments: same pattern — enrolment_id (external ID) and several
-- compliance-relevant fields (opt-out audit trail, re-enrolment due date, worker
-- category, cessation on offboarding) were missing from the original schema.
alter table if exists pension_enrolments add column if not exists enrolment_id          text;
alter table if exists pension_enrolments add column if not exists opt_out_reference     text;
alter table if exists pension_enrolments add column if not exists postponement_end_date date;
alter table if exists pension_enrolments add column if not exists re_enrolment_due_date date;
alter table if exists pension_enrolments add column if not exists worker_category       text;
alter table if exists pension_enrolments add column if not exists updated_at            timestamptz;
alter table if exists pension_enrolments add column if not exists cessation_date        text;
alter table if exists pension_enrolments add column if not exists cessation_reason      text;
create index if not exists pension_enrolments_enrolment_id_idx on pension_enrolments(enrolment_id);

-- employees: link back to the scheme an employee was enrolled into (set by
-- enrol_employee(), was previously silently dropped — no such column existed).
alter table if exists employees add column if not exists pension_scheme_id text;
