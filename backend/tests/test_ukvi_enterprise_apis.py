"""
RealtouchHR - UKVI Compliance and Enterprise Features API Tests
Tests for new UKVI and Enterprise APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rtisync-staging.preview.emergentagent.com')


class TestUKVIComplianceAPIs:
    """Tests for UKVI Compliance Layer APIs"""
    
    def test_ukvi_dashboard_returns_compliance_data(self, authenticated_client):
        """GET /api/ukvi/dashboard - Returns UKVI compliance dashboard"""
        response = authenticated_client.get(f"{BASE_URL}/api/ukvi/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "overall_score" in data
        assert "total_sponsored_employees" in data
        assert "status_breakdown" in data
        assert "disclaimer" in data
        
        # Verify data types
        assert isinstance(data["overall_score"], (int, float))
        assert isinstance(data["total_sponsored_employees"], int)
        assert isinstance(data["status_breakdown"], dict)
        
        # Verify disclaimer is present
        assert "legal advice" in data["disclaimer"].lower()
    
    def test_ukvi_visa_types_returns_list(self, authenticated_client):
        """GET /api/ukvi/visa-types - Returns list of UK visa types"""
        response = authenticated_client.get(f"{BASE_URL}/api/ukvi/visa-types")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "visa_types" in data
        assert isinstance(data["visa_types"], list)
        assert len(data["visa_types"]) > 0
        
        # Verify visa type structure
        visa = data["visa_types"][0]
        assert "code" in visa
        assert "name" in visa
        assert "sponsored" in visa
        
        # Verify known visa types exist
        visa_codes = [v["code"] for v in data["visa_types"]]
        assert "skilled_worker" in visa_codes
        assert "british_citizen" in visa_codes
        assert "settled" in visa_codes
    
    def test_ukvi_alerts_returns_list(self, authenticated_client):
        """GET /api/ukvi/alerts - Returns UKVI compliance alerts"""
        response = authenticated_client.get(f"{BASE_URL}/api/ukvi/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "alerts" in data
        assert "total" in data
        assert isinstance(data["alerts"], list)
        assert isinstance(data["total"], int)
    
    def test_ukvi_alerts_filter_by_resolved(self, authenticated_client):
        """GET /api/ukvi/alerts?resolved=false - Filter alerts by resolved status"""
        response = authenticated_client.get(f"{BASE_URL}/api/ukvi/alerts?resolved=false")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned alerts should be unresolved
        for alert in data["alerts"]:
            assert alert.get("resolved") == False
    
    def test_ukvi_reporting_checklist_returns_data(self, authenticated_client):
        """GET /api/ukvi/reporting/checklist - Returns UKVI reporting checklist"""
        response = authenticated_client.get(f"{BASE_URL}/api/ukvi/reporting/checklist")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "pending_reports" in data
        assert "overdue_reports" in data
        assert "checklist" in data
        assert "disclaimer" in data
        
        # Verify data types
        assert isinstance(data["pending_reports"], int)
        assert isinstance(data["overdue_reports"], int)
        assert isinstance(data["checklist"], list)
        
        # Verify disclaimer mentions 10 working days
        assert "10 working days" in data["disclaimer"]
    
    def test_ukvi_dashboard_requires_auth(self, api_client):
        """GET /api/ukvi/dashboard - Requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/ukvi/dashboard")
        assert response.status_code == 401


class TestEnterpriseAPIs:
    """Tests for Enterprise Features APIs"""
    
    def test_enterprise_roles_returns_list(self, authenticated_client):
        """GET /api/enterprise/roles - Returns list of roles"""
        response = authenticated_client.get(f"{BASE_URL}/api/enterprise/roles")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "roles" in data
        assert "total" in data
        assert isinstance(data["roles"], list)
        assert isinstance(data["total"], int)
    
    def test_enterprise_permissions_returns_categorized_list(self, authenticated_client):
        """GET /api/enterprise/permissions - Returns all available permissions"""
        response = authenticated_client.get(f"{BASE_URL}/api/enterprise/permissions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "permissions" in data
        assert "total" in data
        assert isinstance(data["permissions"], dict)
        
        # Verify permission categories exist
        assert "employee" in data["permissions"]
        assert "payroll" in data["permissions"]
        assert "compliance" in data["permissions"]
        
        # Verify permission structure
        employee_perms = data["permissions"]["employee"]
        assert len(employee_perms) > 0
        assert "code" in employee_perms[0]
        assert "name" in employee_perms[0]
        
        # Verify total count
        assert data["total"] > 0
    
    def test_enterprise_sso_config_returns_status(self, authenticated_client):
        """GET /api/enterprise/sso/config - Returns SSO configuration status"""
        response = authenticated_client.get(f"{BASE_URL}/api/enterprise/sso/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure - either configured or not
        assert "configured" in data or "message" in data
        
        if data.get("configured") == False:
            assert "message" in data
            assert "not configured" in data["message"].lower()
    
    def test_enterprise_roles_requires_auth(self, api_client):
        """GET /api/enterprise/roles - Requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/enterprise/roles")
        assert response.status_code == 401
    
    def test_enterprise_permissions_requires_auth(self, api_client):
        """GET /api/enterprise/permissions - Requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/enterprise/permissions")
        assert response.status_code == 401


class TestRTISyncPollAPI:
    """Tests for RTI Sync Poll API"""
    
    def test_rti_poll_with_submitted_submission(self, authenticated_client):
        """POST /api/rti-sync/submissions/{id}/poll - Poll HMRC for submission status"""
        # First get a submitted submission
        response = authenticated_client.get(f"{BASE_URL}/api/rti-sync/submissions?state=submitted")
        
        if response.status_code != 200:
            pytest.skip("Could not fetch submissions")
        
        data = response.json()
        submitted = [s for s in data.get("submissions", []) if s.get("state") == "submitted"]
        
        if not submitted:
            pytest.skip("No submitted submissions available for polling")
        
        submission_id = submitted[0]["submission_id"]
        
        # Poll the submission
        poll_response = authenticated_client.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/poll"
        )
        
        assert poll_response.status_code == 200
        poll_data = poll_response.json()
        
        # Verify response structure
        assert "status" in poll_data
        assert poll_data["status"] in ["accepted", "rejected", "polling", "pending"]
    
    def test_rti_poll_invalid_submission_returns_404(self, authenticated_client):
        """POST /api/rti-sync/submissions/{id}/poll - Returns 404 for invalid submission"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/rti-sync/submissions/invalid_submission_id/poll"
        )
        assert response.status_code == 404
    
    def test_rti_poll_non_submitted_returns_400(self, authenticated_client):
        """POST /api/rti-sync/submissions/{id}/poll - Returns 400 for non-submitted submission"""
        # Get a submission that's not in submitted state
        response = authenticated_client.get(f"{BASE_URL}/api/rti-sync/submissions")
        
        if response.status_code != 200:
            pytest.skip("Could not fetch submissions")
        
        data = response.json()
        non_submitted = [s for s in data.get("submissions", []) 
                        if s.get("state") not in ["submitted", "polling"]]
        
        if not non_submitted:
            pytest.skip("No non-submitted submissions available")
        
        submission_id = non_submitted[0]["submission_id"]
        
        poll_response = authenticated_client.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/poll"
        )
        
        assert poll_response.status_code == 400
    
    def test_rti_poll_requires_auth(self, api_client):
        """POST /api/rti-sync/submissions/{id}/poll - Requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/rti-sync/submissions/any_id/poll"
        )
        assert response.status_code == 401


class TestDashboardAPI:
    """Tests for Dashboard API"""
    
    def test_dashboard_stats_returns_compliance_score(self, authenticated_client):
        """GET /api/dashboard/stats - Returns compliance score"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify compliance score is present
        assert "compliance_score" in data
        assert isinstance(data["compliance_score"], (int, float))
        assert 0 <= data["compliance_score"] <= 100
