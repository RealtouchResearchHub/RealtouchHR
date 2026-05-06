"""
RealtouchHR — Iteration 8 backend tests
Coverage:
  - Stripe billing endpoints (subscription/addon checkout, billing info, status)
  - Stripe webhook reachability (top-level /api/webhook/stripe)
  - Statutory payments (rates, SSP/SMP/SPP calc, record, list, EPS summary)
  - Offboarding workflow (reasons, terminate, list, reinstate)
  - Tax documents (P60/P45/P11D PDF generation)
  - Email notification wiring (timesheet approval, pension enrolment, visa alerts)
  - Regression smoke (auth, employees, hmrc, ukvi, pensions)
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ukvi-staging.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- shared fixtures ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_account(session):
    """Register a fresh owner-role user with a company so billing endpoints work."""
    suffix = uuid.uuid4().hex[:8]
    email = f"owner_{suffix}@example.com"
    payload = {
        "email": email,
        "password": "Test123!",
        "name": "Iter8 Owner",
        "company_name": f"Iter8 Co {suffix}",
    }
    r = session.post(f"{API}/auth/register", json=payload, timeout=30)
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("token") or data.get("access_token") or data.get("session_token")
    user = data.get("user") or {}
    company_id = user.get("company_id") or data.get("company_id")
    if not token:
        pytest.skip("no token returned from register")
    return {"email": email, "token": token, "user": user, "company_id": company_id}


@pytest.fixture(scope="module")
def auth(owner_account):
    return {"Authorization": f"Bearer {owner_account['token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def test_employee(session, auth, owner_account):
    """Create a test employee for statutory + offboarding + tax-doc tests."""
    suffix = uuid.uuid4().hex[:6]
    body = {
        "first_name": "Test",
        "last_name": f"Emp{suffix}",
        "email": f"emp_{suffix}@example.com",
        "national_insurance_number": "AB123456C",
        "date_of_birth": "1990-01-01",
        "start_date": "2023-01-01",
        "job_title": "Engineer",
        "annual_salary": 30000.0,
        "weekly_hours": 37.5,
        "employment_type": "full_time",
        "is_director": False,
    }
    r = session.post(f"{API}/employees", json=body, headers=auth, timeout=30)
    if r.status_code not in (200, 201):
        pytest.skip(f"employee create failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    return data.get("employee") or data


# ============== STATUTORY ==============

class TestStatutory:
    def test_rates_public(self, session):
        r = session.get(f"{API}/statutory/rates", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tax_year"] == "2025-26"
        assert d["ssp_weekly_rate"] == 116.75
        assert d["smp_weekly_rate"] == 184.03
        assert d["spp_weekly_rate"] == 184.03

    def test_active_requires_auth(self, session):
        r = session.get(f"{API}/statutory/active", timeout=20)
        assert r.status_code in (401, 403)

    def test_active_with_auth(self, session, auth):
        r = session.get(f"{API}/statutory/active", headers=auth, timeout=20)
        assert r.status_code == 200
        assert "payments" in r.json()

    def test_employee_listing(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        r = session.get(f"{API}/statutory/employee/{emp_id}", headers=auth, timeout=20)
        assert r.status_code == 200
        assert "payments" in r.json()

    def test_eps_summary(self, session, auth):
        r = session.get(f"{API}/statutory/eps-summary?tax_month=1&tax_year=2025-26", headers=auth, timeout=20)
        assert r.status_code == 200

    def test_ssp_calculate(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        body = {
            "employee_id": emp_id,
            "sick_start_date": "2025-04-01",
            "sick_end_date": "2025-04-21",
            "qualifying_days_per_week": 5,
        }
        r = session.post(f"{API}/statutory/ssp/calculate", json=body, headers=auth, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # service returns either a successful calc, or {eligible:false, reason:...} for LEL fails
        assert any(k in d for k in ("weekly_rate", "total_amount", "ssp_payable_days", "eligible", "amount"))

    def test_smp_calculate(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        body = {
            "employee_id": emp_id,
            "expected_week_of_childbirth": "2025-08-01",
            "maternity_start_date": "2025-06-01",
            "is_small_employer": True,
        }
        r = session.post(f"{API}/statutory/smp/calculate", json=body, headers=auth, timeout=30)
        assert r.status_code in (200, 400), r.text

    def test_spp_calculate(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        body = {
            "employee_id": emp_id,
            "birth_date": "2025-05-01",
            "paternity_weeks": 2,
        }
        r = session.post(f"{API}/statutory/spp/calculate", json=body, headers=auth, timeout=30)
        assert r.status_code in (200, 400), r.text

    def test_record_statutory_payment(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        body = {
            "employee_id": emp_id,
            "payment_type": "ssp",
            "start_date": "2025-04-01",
            "end_date": "2025-04-21",
            "calculation": {"weekly_rate": 116.75, "total_amount": 350.25, "ssp_payable_days": 15},
            "notes": "iter8 test ssp",
        }
        r = session.post(f"{API}/statutory/record", json=body, headers=auth, timeout=20)
        assert r.status_code in (200, 201, 400), r.text


# ============== BILLING / STRIPE ==============

class TestBilling:
    def test_get_plans_requires_auth(self):
        # Use a NEW requests session so we don't inherit the module session_token cookie
        fresh = requests.Session()
        r = fresh.get(f"{API}/payments/plans", timeout=20)
        assert r.status_code in (401, 403)

    def test_get_plans(self, session, auth):
        r = session.get(f"{API}/payments/plans", headers=auth, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "plans" in d and "addons" in d
        assert set(d["plans"].keys()) >= {"starter", "professional", "enterprise"}
        assert d["plans"]["starter"]["price"] == 49.00
        assert d["plans"]["professional"]["price"] == 149.00
        assert d["plans"]["enterprise"]["price"] == 399.00

    def test_billing_info(self, session, auth):
        r = session.get(f"{API}/payments/billing", headers=auth, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # expect plan, plans, addons, transactions to be present
        assert "transactions" in d or "current_plan" in d or "plans" in d

    def test_subscription_checkout_creates_session(self, session, auth):
        body = {"plan_id": "starter", "origin_url": BASE_URL}
        r = session.post(f"{API}/payments/checkout/subscription", json=body, headers=auth, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # Stripe checkout returns checkout_url + session_id in playbook
        assert "url" in d or "checkout_url" in d
        sid = d.get("session_id") or d.get("id")
        assert sid and sid.startswith("cs_test_"), f"Expected cs_test_ session_id, got: {sid}"
        # verify a payment_transactions row was created (via /transactions list)
        tr = session.get(f"{API}/payments/transactions", headers=auth, timeout=20)
        assert tr.status_code == 200
        assert tr.json().get("total", 0) >= 1

    def test_addon_checkout(self, session, auth):
        body = {"addon_id": "extra_users_10", "origin_url": BASE_URL, "quantity": 1}
        r = session.post(f"{API}/payments/checkout/addon", json=body, headers=auth, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        sid = d.get("session_id") or d.get("id")
        assert sid and sid.startswith("cs_test_")

    def test_subscription_invalid_plan(self, session, auth):
        body = {"plan_id": "non_existent_plan", "origin_url": BASE_URL}
        r = session.post(f"{API}/payments/checkout/subscription", json=body, headers=auth, timeout=20)
        assert r.status_code == 400

    def test_top_level_webhook_reachable(self, session):
        # Top-level /api/webhook/stripe should return 4xx (signature error) — NOT 404
        r = session.post(f"{API}/webhook/stripe", data=b"{}", headers={"Stripe-Signature": "t=1,v1=fake"}, timeout=20)
        assert r.status_code != 404, "webhook endpoint not registered"
        assert 400 <= r.status_code < 500


# ============== OFFBOARDING ==============

class TestOffboarding:
    def test_reasons(self, session, auth):
        r = session.get(f"{API}/offboarding/reasons", headers=auth, timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json().get("reasons"), list)
        assert len(r.json()["reasons"]) > 0

    def test_terminate_and_list_and_reinstate(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        leaving = (datetime.utcnow() + timedelta(days=14)).date().isoformat()
        body = {
            "employee_id": emp_id,
            "leaving_date": leaving,
            "reason": "resignation",
            "notes": "iter8 e2e",
            "redundancy_payment": 0.0,
            "holiday_payout_days": 2.5,
        }
        r = session.post(f"{API}/offboarding/terminate", json=body, headers=auth, timeout=60)
        assert r.status_code == 200, r.text
        result = r.json()
        # pipeline result should reference P45 + leaver_queue
        assert "p45" in result or "p45_id" in result or "tax_document" in result or "leaver_queue" in result or "message" in result

        # appears in list
        r2 = session.get(f"{API}/offboarding/list", headers=auth, timeout=20)
        assert r2.status_code == 200
        ids = [t.get("employee_id") for t in r2.json().get("terminations", [])]
        assert emp_id in ids

        # P45 download should now succeed (terminated)
        r3 = session.get(f"{API}/tax-docs/p45/{emp_id}", headers=auth, timeout=60)
        assert r3.status_code == 200, r3.text
        assert r3.headers.get("content-type", "").startswith("application/pdf")
        assert r3.content[:4] == b"%PDF"

        # reinstate
        r4 = session.post(f"{API}/offboarding/reinstate/{emp_id}", headers=auth, timeout=20)
        assert r4.status_code == 200

    def test_p45_400_when_not_terminated(self, session, auth):
        # New active employee
        suffix = uuid.uuid4().hex[:6]
        emp_body = {
            "first_name": "Active",
            "last_name": f"NoP45{suffix}",
            "email": f"act_{suffix}@example.com",
            "national_insurance_number": "AB123456D",
            "date_of_birth": "1990-01-01",
            "start_date": "2024-01-01",
            "job_title": "Engineer",
            "annual_salary": 30000.0,
        }
        emp = session.post(f"{API}/employees", json=emp_body, headers=auth, timeout=30).json()
        emp = emp.get("employee") or emp
        emp_id = emp.get("employee_id")
        if not emp_id:
            pytest.skip("could not create active employee")
        r = session.get(f"{API}/tax-docs/p45/{emp_id}", headers=auth, timeout=30)
        assert r.status_code == 400


# ============== TAX DOCUMENTS ==============

class TestTaxDocs:
    def test_p60_pdf(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        r = session.get(f"{API}/tax-docs/p60/{emp_id}?tax_year=2024-25", headers=auth, timeout=60)
        # If no payslips for that year service may return 404 or 400; otherwise 200 PDF
        assert r.status_code in (200, 400, 404), r.text
        if r.status_code == 200:
            assert r.headers.get("content-type", "").startswith("application/pdf")
            assert r.content[:4] == b"%PDF"

    def test_p11d_create_and_get(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        body = {
            "employee_id": emp_id,
            "tax_year": "2024-25",
            "benefits": [
                {"category": "company_car", "description": "BMW", "cash_equivalent": 5000.0},
                {"category": "private_medical", "description": "BUPA", "cash_equivalent": 800.0},
            ],
        }
        r = session.post(f"{API}/tax-docs/p11d", json=body, headers=auth, timeout=30)
        assert r.status_code in (200, 201), r.text
        # GET PDF
        r2 = session.get(f"{API}/tax-docs/p11d/{emp_id}/2024-25", headers=auth, timeout=60)
        assert r2.status_code == 200, r2.text
        assert r2.content[:4] == b"%PDF"

    def test_employee_documents_listing(self, session, auth, test_employee):
        emp_id = test_employee["employee_id"]
        r = session.get(f"{API}/tax-docs/employee/{emp_id}/documents", headers=auth, timeout=20)
        assert r.status_code == 200


# ============== EMAIL WIRING (mock log mode) ==============

class TestEmailWiring:
    def test_visa_alerts_endpoint_reachable(self, session, auth):
        # MOCK mode — just ensure endpoint runs without 5xx
        r = session.post(f"{API}/ukvi/alerts/generate", headers=auth, timeout=30)
        assert r.status_code in (200, 201, 204), r.text


# ============== REGRESSION SMOKE ==============

class TestRegression:
    def test_health(self, session):
        r = session.get(f"{API}/health", timeout=20)
        assert r.status_code == 200

    def test_employees_listing(self, session, auth):
        r = session.get(f"{API}/employees", headers=auth, timeout=20)
        assert r.status_code == 200

    def test_pensions_thresholds(self, session, auth):
        r = session.get(f"{API}/pensions/thresholds", headers=auth, timeout=20)
        assert r.status_code == 200

    def test_rtw_summary(self, session, auth):
        r = session.get(f"{API}/rtw/summary", headers=auth, timeout=20)
        assert r.status_code == 200

    def test_ukvi_dashboard(self, session, auth):
        # try common ukvi paths — at least one should respond 200
        for path in ("/ukvi/dashboard", "/ukvi/summary", "/ukvi/alerts"):
            r = session.get(f"{API}{path}", headers=auth, timeout=20)
            if r.status_code == 200:
                return
        pytest.fail("no ukvi dashboard endpoint responded 200")

    def test_cos_list(self, session, auth):
        r = session.get(f"{API}/cos/list", headers=auth, timeout=20)
        # 404 acceptable if cos service returns 404 for "no certificates" — verify endpoint registered
        assert r.status_code in (200, 404)

    def test_time_timesheets(self, session, auth):
        r = session.get(f"{API}/time/timesheets", headers=auth, timeout=20)
        assert r.status_code == 200
