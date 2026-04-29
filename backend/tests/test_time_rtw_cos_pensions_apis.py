"""
Backend API tests for Time & Scheduling, RTW, CoS, and Pensions modules
"""
import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rtisync-staging.preview.emergentagent.com')


class TestTimeSchedulingAPIs:
    """Tests for Time & Scheduling endpoints"""
    
    def test_time_status_returns_clock_status(self, authenticated_client):
        """GET /api/time/status - returns current clock status"""
        response = authenticated_client.get(f"{BASE_URL}/api/time/status")
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}, {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["not_clocked_in", "clocked_in", "on_break"]
    
    def test_time_status_requires_auth(self, api_client):
        """GET /api/time/status - requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/time/status")
        assert response.status_code == 401
    
    def test_time_shifts_returns_shifts(self, authenticated_client):
        """GET /api/time/shifts - returns shifts for date range"""
        today = date.today()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=7)
        
        response = authenticated_client.get(
            f"{BASE_URL}/api/time/shifts",
            params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "shifts" in data
        assert "total" in data
        assert isinstance(data["shifts"], list)
    
    def test_time_rotas_returns_rotas(self, authenticated_client):
        """GET /api/time/rotas - returns rotas list"""
        response = authenticated_client.get(f"{BASE_URL}/api/time/rotas")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "rotas" in data
        assert "total" in data
        assert isinstance(data["rotas"], list)
    
    def test_time_timesheets_returns_timesheets(self, authenticated_client):
        """GET /api/time/timesheets - returns timesheets list"""
        response = authenticated_client.get(f"{BASE_URL}/api/time/timesheets")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "timesheets" in data
        assert "total" in data
        assert isinstance(data["timesheets"], list)
    
    def test_clock_in_requires_auth(self, api_client):
        """POST /api/time/clock-in - requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/time/clock-in", json={})
        assert response.status_code == 401
    
    def test_clock_out_requires_auth(self, api_client):
        """POST /api/time/clock-out - requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/time/clock-out", json={})
        assert response.status_code == 401


class TestRTWAPIs:
    """Tests for Right to Work endpoints"""
    
    def test_rtw_summary_returns_summary(self, authenticated_client):
        """GET /api/rtw/summary - returns RTW status summary"""
        response = authenticated_client.get(f"{BASE_URL}/api/rtw/summary")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "total_employees" in data
        assert "valid" in data
        assert "permanent" in data
        assert "expiring_soon" in data
        assert "expired" in data
        assert "not_checked" in data
    
    def test_rtw_check_types_returns_types(self, authenticated_client):
        """GET /api/rtw/check-types - returns available check types"""
        response = authenticated_client.get(f"{BASE_URL}/api/rtw/check-types")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "check_types" in data
        assert isinstance(data["check_types"], list)
        assert len(data["check_types"]) > 0
        # Verify structure
        for check_type in data["check_types"]:
            assert "code" in check_type
            assert "name" in check_type
    
    def test_rtw_expiring_returns_expiring_employees(self, authenticated_client):
        """GET /api/rtw/expiring - returns employees with expiring RTW"""
        response = authenticated_client.get(f"{BASE_URL}/api/rtw/expiring")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "employees" in data
        assert "total" in data
        assert "days" in data
        assert isinstance(data["employees"], list)
    
    def test_rtw_expiring_with_custom_days(self, authenticated_client):
        """GET /api/rtw/expiring?days=90 - accepts custom days parameter"""
        response = authenticated_client.get(f"{BASE_URL}/api/rtw/expiring", params={"days": 90})
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert data["days"] == 90
    
    def test_rtw_summary_requires_auth(self, api_client):
        """GET /api/rtw/summary - requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/rtw/summary")
        assert response.status_code == 401


class TestCoSAPIs:
    """Tests for Certificate of Sponsorship endpoints"""
    
    def test_cos_list_returns_certificates(self, authenticated_client):
        """GET /api/cos - returns list of certificates"""
        response = authenticated_client.get(f"{BASE_URL}/api/cos")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "certificates" in data
        assert "total" in data
        assert isinstance(data["certificates"], list)
    
    def test_cos_soc_codes_search(self, authenticated_client):
        """GET /api/cos/soc-codes/search?query=IT - searches SOC codes"""
        response = authenticated_client.get(f"{BASE_URL}/api/cos/soc-codes/search", params={"query": "IT"})
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "soc_codes" in data
        assert "total" in data
        assert isinstance(data["soc_codes"], list)
        # Should find IT-related SOC codes
        if data["total"] > 0:
            for soc in data["soc_codes"]:
                assert "soc_code" in soc
                assert "title" in soc
                assert "going_rate_annual" in soc
    
    def test_cos_salary_checks_returns_issues(self, authenticated_client):
        """GET /api/cos/salary-checks - returns salary threshold issues"""
        response = authenticated_client.get(f"{BASE_URL}/api/cos/salary-checks")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "issues" in data
        assert "total_issues" in data
        assert "general_threshold" in data
        assert "new_entrant_threshold" in data
        assert isinstance(data["issues"], list)
    
    def test_cos_list_requires_auth(self, api_client):
        """GET /api/cos - requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/cos")
        assert response.status_code == 401


class TestPensionsAPIs:
    """Tests for Pension Auto-Enrolment endpoints"""
    
    def test_pensions_thresholds_returns_thresholds(self, authenticated_client):
        """GET /api/pensions/thresholds - returns auto-enrolment thresholds"""
        response = authenticated_client.get(f"{BASE_URL}/api/pensions/thresholds")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "lower_qualifying_earnings" in data
        assert "earnings_trigger" in data
        assert "upper_qualifying_earnings" in data
        assert "state_pension_age" in data
        assert "min_employer_contribution_pct" in data
        assert "min_total_contribution_pct" in data
        assert "tax_year" in data
        # Verify values are reasonable
        assert data["lower_qualifying_earnings"] > 0
        assert data["earnings_trigger"] > data["lower_qualifying_earnings"]
        assert data["upper_qualifying_earnings"] > data["earnings_trigger"]
    
    def test_pensions_schemes_returns_schemes(self, authenticated_client):
        """GET /api/pensions/schemes - returns pension schemes list"""
        response = authenticated_client.get(f"{BASE_URL}/api/pensions/schemes")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "schemes" in data
        assert "total" in data
        assert isinstance(data["schemes"], list)
    
    def test_pensions_bulk_assess_runs_assessment(self, authenticated_client):
        """POST /api/pensions/assess - runs bulk auto-enrolment assessment"""
        response = authenticated_client.post(f"{BASE_URL}/api/pensions/assess")
        assert response.status_code == 200, f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        assert "total_assessed" in data
        assert "eligible_jobholders_count" in data
        assert "non_eligible_count" in data
        assert "entitled_workers_count" in data
        assert "to_enrol_count" in data
    
    def test_pensions_thresholds_requires_auth(self, api_client):
        """GET /api/pensions/thresholds - requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/pensions/thresholds")
        assert response.status_code == 401
