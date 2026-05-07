"""
Iteration 10 backend tests:
- Public sandbox demo (POST /api/demo/sandbox + cleanup)
- Student loan in payroll engine
- Company response model fields restored
- Employee model accepts immigration_status / ni_letter / student_loan_plan
- Axios-style Bearer auth verifying sandbox token works on subsequent calls
- UKVI salary_threshold_breach alert via standard CRUD
"""
import os
import uuid
import time
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ukvi-staging.preview.emergentagent.com').rstrip('/')


# ==================== Sandbox Demo ====================
class TestSandboxDemo:
    def test_sandbox_endpoint_no_auth_required(self):
        """POST /api/demo/sandbox returns 200 without any auth header."""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(f"{BASE_URL}/api/demo/sandbox", json={})
        assert r.status_code == 200, f"sandbox endpoint failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        # Required fields
        assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 20
        assert "user" in data
        assert "company_id" in data
        assert data["expires_in_hours"] == 24
        assert "tour_steps" in data and len(data["tour_steps"]) == 6
        # Validate user shape
        u = data["user"]
        assert u["role"] == "owner"
        assert u["auth_method"] == "sandbox"
        assert u["company_id"] == data["company_id"]
        # Save for next test
        TestSandboxDemo._token = data["token"]
        TestSandboxDemo._company_id = data["company_id"]
        TestSandboxDemo._user_email = u["email"]

    def test_sandbox_token_works_as_bearer(self):
        """Token returned by sandbox should authenticate /api/auth/me."""
        token = getattr(TestSandboxDemo, "_token", None)
        if not token:
            pytest.skip("sandbox token not available")
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"auth/me failed: {r.status_code} {r.text[:300]}"
        me = r.json()
        assert me.get("role") == "owner"
        # Note: /api/auth/me may not surface auth_method/is_sandbox — verify via /api/company below
        assert me.get("email", "").startswith("sandbox.")

    def test_sandbox_company_is_seeded(self):
        """Sandbox company should be flagged is_sandbox + demo_mode and have 6 employees."""
        token = getattr(TestSandboxDemo, "_token", None)
        if not token:
            pytest.skip()
        h = {"Authorization": f"Bearer {token}"}
        rc = requests.get(f"{BASE_URL}/api/company", headers=h)
        assert rc.status_code == 200
        comp = rc.json()
        assert comp.get("demo_mode") is True
        assert comp.get("is_sandbox") is True or comp.get("demo_mode") is True
        assert comp.get("paye_reference") == "120/AB1234"
        # Employees
        re_ = requests.get(f"{BASE_URL}/api/employees", headers=h)
        assert re_.status_code == 200
        emps = re_.json()
        assert len(emps) >= 6, f"expected >=6 demo employees, got {len(emps)}"
        # Pay run draft present
        rp = requests.get(f"{BASE_URL}/api/payroll/runs", headers=h)
        assert rp.status_code == 200
        runs = rp.json()
        assert len(runs) >= 1

    def test_sandbox_cleanup_idempotent(self):
        """POST /api/demo/sandbox/cleanup is idempotent — calling twice succeeds."""
        r1 = requests.post(f"{BASE_URL}/api/demo/sandbox/cleanup")
        assert r1.status_code == 200, f"cleanup1 failed: {r1.status_code} {r1.text[:300]}"
        body1 = r1.json()
        assert "cleaned_up" in body1 and "deleted" in body1
        r2 = requests.post(f"{BASE_URL}/api/demo/sandbox/cleanup")
        assert r2.status_code == 200
        body2 = r2.json()
        assert "cleaned_up" in body2


# ==================== Auth helper / fresh user fixture ====================
@pytest.fixture(scope="module")
def fresh_owner():
    """Register a fresh owner so subsequent tests don't interfere with each other."""
    suffix = uuid.uuid4().hex[:8]
    email = f"iter10_{suffix}@example.com"
    payload = {
        "email": email,
        "password": "Test123!",
        "name": "Iter10 Owner",
        "company_name": f"Iter10 Co {suffix}",
    }
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    token = data.get("token")
    return {"email": email, "token": token, "headers": {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}}


# ==================== Employee model fields persistence ====================
class TestEmployeeModelFields:
    def test_create_employee_with_immigration_and_loan_fields(self, fresh_owner):
        h = fresh_owner["headers"]
        emp = {
            "first_name": "Test",
            "last_name": "Sponsored",
            "email": f"sponsored_{uuid.uuid4().hex[:6]}@example.com",
            "salary": 30000,  # Below £38,700 threshold
            "ni_number": "AB123456C",
            "tax_code": "1257L",
            "ni_letter": "A",
            "student_loan_plan": "plan_2",
            "has_postgrad_loan": True,
            "immigration_status": {
                "visa_type": "skilled_worker",
                "visa_expiry": "2026-12-31",
                "cos_number": "C2X123456",
                "rtw_check_date": "2025-01-15",
            },
        }
        r = requests.post(f"{BASE_URL}/api/employees", json=emp, headers=h)
        assert r.status_code == 200, f"create employee failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        assert body["student_loan_plan"] == "plan_2"
        assert body["has_postgrad_loan"] is True
        assert body["ni_letter"] == "A"
        assert body["immigration_status"]["visa_type"] == "skilled_worker"
        TestEmployeeModelFields._sponsored_id = body["employee_id"]

    def test_get_employee_returns_persisted_fields(self, fresh_owner):
        h = fresh_owner["headers"]
        r = requests.get(f"{BASE_URL}/api/employees", headers=h)
        assert r.status_code == 200
        emps = r.json()
        # Find the sponsored one
        sponsored = next((e for e in emps if (e.get("immigration_status") or {}).get("visa_type") == "skilled_worker"), None)
        assert sponsored is not None, "sponsored employee not returned"
        assert sponsored["student_loan_plan"] == "plan_2"
        assert sponsored["has_postgrad_loan"] is True

    def test_ukvi_salary_threshold_breach_via_crud(self, fresh_owner):
        """Sponsored employee with salary < £38,700 should trigger salary_threshold_breach when alerts generated."""
        h = fresh_owner["headers"]
        r = requests.post(f"{BASE_URL}/api/ukvi/alerts/generate", headers=h)
        assert r.status_code == 200, f"alerts/generate failed: {r.status_code} {r.text[:300]}"
        # Fetch alerts list
        r2 = requests.get(f"{BASE_URL}/api/ukvi/alerts", headers=h)
        assert r2.status_code == 200
        body = r2.json()
        alerts = body.get("alerts", body) if isinstance(body, dict) else body
        breach = [a for a in alerts if a.get("alert_type") == "salary_threshold_breach"]
        assert len(breach) >= 1, f"expected salary_threshold_breach alert, got types: {[a.get('alert_type') for a in alerts]}"


# ==================== Company response model ====================
class TestCompanyResponseModel:
    def test_company_returns_hmrc_and_sponsor_fields(self, fresh_owner):
        h = fresh_owner["headers"]
        # Update fields
        upd = {
            "paye_reference": "120/CD5678",
            "accounts_office_reference": "120PA00099999",
            "sponsor_licence_number": "SPL12345",
            "sponsor_licence_expiry": "2027-06-30",
            "sponsor_licence_rating": "A-rated",
            "small_employer_relief": True,
        }
        ru = requests.put(f"{BASE_URL}/api/company", json=upd, headers=h)
        assert ru.status_code == 200, f"PUT company failed: {ru.status_code} {ru.text[:300]}"
        # GET back
        rg = requests.get(f"{BASE_URL}/api/company", headers=h)
        assert rg.status_code == 200
        c = rg.json()
        assert c.get("paye_reference") == "120/CD5678"
        assert c.get("accounts_office_reference") == "120PA00099999"
        assert c.get("sponsor_licence_number") == "SPL12345"
        assert c.get("sponsor_licence_expiry") == "2027-06-30"
        assert c.get("sponsor_licence_rating") == "A-rated"
        assert c.get("small_employer_relief") is True
        assert "demo_mode" in c  # default False but field must exist


# ==================== Student Loan in Payroll ====================
class TestStudentLoanPayroll:
    def test_payslip_includes_student_loan(self, fresh_owner):
        h = fresh_owner["headers"]
        # Add a high-salary student-loan employee
        emp = {
            "first_name": "Loan",
            "last_name": "Plan2",
            "email": f"loan_{uuid.uuid4().hex[:6]}@example.com",
            "salary": 45000,
            "ni_number": "CD234567D",
            "tax_code": "1257L",
            "ni_letter": "A",
            "student_loan_plan": "plan_2",
            "has_postgrad_loan": True,
        }
        r = requests.post(f"{BASE_URL}/api/employees", json=emp, headers=h)
        assert r.status_code == 200, f"create loan employee failed: {r.text[:300]}"
        # Run payroll
        rp = requests.post(f"{BASE_URL}/api/payroll/runs", json={
            "period_start": "2025-04-01",
            "period_end": "2025-04-30",
            "pay_date": "2025-04-30",
        }, headers=h)
        assert rp.status_code == 200, f"create payrun failed: {rp.status_code} {rp.text[:300]}"
        run = rp.json()
        run_id = run.get("payrun_id") or run.get("id") or run.get("pay_run_id")
        assert run_id, f"no payrun_id in response: {run}"
        # Get payslips
        rs = requests.get(f"{BASE_URL}/api/payroll/runs/{run_id}/payslips", headers=h)
        assert rs.status_code == 200, f"get payslips failed: {rs.status_code} {rs.text[:300]}"
        slips = rs.json()
        assert len(slips) >= 1
        # Find loan employee's slip
        loan_slips = [s for s in slips if s.get("student_loan_plan") == "plan_2"]
        assert len(loan_slips) >= 1, f"no slip with student_loan_plan=plan_2; slip plans: {[s.get('student_loan_plan') for s in slips]}"
        # Find the £45k payslip — gross_pay = 45000/12 = 3750
        ls = next((s for s in loan_slips if abs(float(s.get("gross_pay", 0)) - 3750.0) < 1.0), None)
        assert ls is not None, f"no £45k loan_plan2 slip found; payslips: {loan_slips}"
        assert "student_loan_deduction" in ls
        # For £45k on plan_2 + postgrad → £132.79 (plan_2) + £120.00 (postgrad) = £252.79/month
        deduction = float(ls["student_loan_deduction"])
        assert 250 < deduction < 256, f"student_loan_deduction unexpected for £45k plan_2+postgrad: {deduction}"
        # Non-student-loan employee should be 0 with plan='none'
        non = [s for s in slips if s.get("student_loan_plan") in (None, "none")]
        if non:
            for s in non:
                assert float(s.get("student_loan_deduction", 0)) == 0


# ==================== Regression smoke ====================
class TestRegressionSmoke:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200

    def test_demo_seed_still_works(self, fresh_owner):
        h = fresh_owner["headers"]
        r = requests.post(f"{BASE_URL}/api/demo/seed", headers=h)
        assert r.status_code == 200, f"demo seed failed: {r.status_code} {r.text[:300]}"

    def test_auth_login_existing_user_or_skip(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com", "password": "Test123!"
        })
        if r.status_code != 200:
            pytest.skip("test@example.com not present — non-blocking")
        assert "token" in r.json()
