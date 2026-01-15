"""
RealtouchHR - HMRC RTI and Self-Service API Tests
Tests for new features: HMRC RTI submissions and Employee Self-Service Portal
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "Test123!"


class TestHMRCRoutes:
    """Tests for HMRC RTI submission endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.user = data.get("user")
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_hmrc_submissions_list(self):
        """Test GET /api/hmrc/submissions - Get RTI submission history"""
        response = self.session.get(f"{BASE_URL}/api/hmrc/submissions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of submissions"
        print(f"✓ HMRC submissions list: {len(data)} submissions found")
    
    def test_hmrc_validate_payrun_no_payrun(self):
        """Test POST /api/hmrc/validate/{payrun_id} - Validate non-existent pay run"""
        response = self.session.post(f"{BASE_URL}/api/hmrc/validate/nonexistent_payrun")
        
        # Should return 404 for non-existent pay run
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ HMRC validate returns 404 for non-existent pay run")
    
    def test_hmrc_health_check_no_payrun(self):
        """Test GET /api/hmrc/health-check/{payrun_id} - Health check non-existent pay run"""
        response = self.session.get(f"{BASE_URL}/api/hmrc/health-check/nonexistent_payrun")
        
        # Should return 404 for non-existent pay run
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ HMRC health check returns 404 for non-existent pay run")
    
    def test_hmrc_fps_submit_no_payrun(self):
        """Test POST /api/hmrc/fps/submit - Submit FPS for non-existent pay run"""
        response = self.session.post(f"{BASE_URL}/api/hmrc/fps/submit", json={
            "payrun_id": "nonexistent_payrun",
            "submission_type": "FPS",
            "test_mode": True
        })
        
        # Should return 404 for non-existent pay run
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ HMRC FPS submit returns 404 for non-existent pay run")


class TestHMRCWithPayRun:
    """Tests for HMRC RTI with actual pay run data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.user = data.get("user")
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_get_existing_payruns(self):
        """Get existing pay runs to use for HMRC tests"""
        response = self.session.get(f"{BASE_URL}/api/payroll/runs")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ Found {len(data)} pay runs")
        
        if data:
            self.payrun_id = data[0].get("payrun_id")
            print(f"  Using pay run: {self.payrun_id}")
            return self.payrun_id
        return None
    
    def test_hmrc_validate_existing_payrun(self):
        """Test HMRC validation with existing pay run"""
        # First get a pay run
        runs_response = self.session.get(f"{BASE_URL}/api/payroll/runs")
        if runs_response.status_code != 200 or not runs_response.json():
            pytest.skip("No pay runs available for testing")
        
        payrun_id = runs_response.json()[0].get("payrun_id")
        
        response = self.session.post(f"{BASE_URL}/api/hmrc/validate/{payrun_id}")
        
        # Should return 200 with validation result
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "valid" in data, "Response should contain 'valid' field"
        assert "errors" in data, "Response should contain 'errors' field"
        assert "warnings" in data, "Response should contain 'warnings' field"
        print(f"✓ HMRC validation result: valid={data.get('valid')}, errors={len(data.get('errors', []))}, warnings={len(data.get('warnings', []))}")
    
    def test_hmrc_health_check_existing_payrun(self):
        """Test HMRC health check with existing pay run"""
        # First get a pay run
        runs_response = self.session.get(f"{BASE_URL}/api/payroll/runs")
        if runs_response.status_code != 200 or not runs_response.json():
            pytest.skip("No pay runs available for testing")
        
        payrun_id = runs_response.json()[0].get("payrun_id")
        
        response = self.session.get(f"{BASE_URL}/api/hmrc/health-check/{payrun_id}")
        
        # Should return 200 with health check result
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "payrun_id" in data, "Response should contain 'payrun_id'"
        assert "overall_status" in data, "Response should contain 'overall_status'"
        assert "score" in data, "Response should contain 'score'"
        assert "issues" in data, "Response should contain 'issues'"
        assert "can_proceed" in data, "Response should contain 'can_proceed'"
        
        print(f"✓ HMRC health check: status={data.get('overall_status')}, score={data.get('score')}, can_proceed={data.get('can_proceed')}")
        print(f"  Issues found: {len(data.get('issues', []))}")


class TestSelfServiceRoutes:
    """Tests for Employee Self-Service Portal endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.user = data.get("user")
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_self_service_profile(self):
        """Test GET /api/self-service/profile - Get employee profile"""
        response = self.session.get(f"{BASE_URL}/api/self-service/profile")
        
        # May return 403 if user is not linked to an employee
        if response.status_code == 403:
            print("✓ Self-service profile returns 403 (user not linked to employee) - expected for admin users")
            return
        
        assert response.status_code == 200, f"Expected 200 or 403, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "employee_id" in data, "Response should contain 'employee_id'"
        assert "first_name" in data, "Response should contain 'first_name'"
        assert "last_name" in data, "Response should contain 'last_name'"
        print(f"✓ Self-service profile: {data.get('first_name')} {data.get('last_name')}")
    
    def test_self_service_payslips(self):
        """Test GET /api/self-service/payslips - Get employee payslips"""
        response = self.session.get(f"{BASE_URL}/api/self-service/payslips")
        
        # May return 403 if user is not linked to an employee
        if response.status_code == 403:
            print("✓ Self-service payslips returns 403 (user not linked to employee) - expected for admin users")
            return
        
        assert response.status_code == 200, f"Expected 200 or 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of payslips"
        print(f"✓ Self-service payslips: {len(data)} payslips found")
    
    def test_self_service_leave_balance(self):
        """Test GET /api/self-service/leave/balance - Get leave balance"""
        response = self.session.get(f"{BASE_URL}/api/self-service/leave/balance")
        
        # May return 403 if user is not linked to an employee
        if response.status_code == 403:
            print("✓ Self-service leave balance returns 403 (user not linked to employee) - expected for admin users")
            return
        
        assert response.status_code == 200, f"Expected 200 or 403, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "employee_id" in data, "Response should contain 'employee_id'"
        assert "annual_entitlement" in data, "Response should contain 'annual_entitlement'"
        assert "remaining" in data, "Response should contain 'remaining'"
        print(f"✓ Self-service leave balance: {data.get('remaining')}/{data.get('annual_entitlement')} days remaining")
    
    def test_self_service_leave_requests(self):
        """Test GET /api/self-service/leave/requests - Get leave requests"""
        response = self.session.get(f"{BASE_URL}/api/self-service/leave/requests")
        
        # May return 403 if user is not linked to an employee
        if response.status_code == 403:
            print("✓ Self-service leave requests returns 403 (user not linked to employee) - expected for admin users")
            return
        
        assert response.status_code == 200, f"Expected 200 or 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of leave requests"
        print(f"✓ Self-service leave requests: {len(data)} requests found")
    
    def test_self_service_profile_update(self):
        """Test PUT /api/self-service/profile - Update employee profile"""
        response = self.session.put(f"{BASE_URL}/api/self-service/profile", json={
            "phone": "07123456789",
            "address": "123 Test Street, London"
        })
        
        # May return 403 or 404 if user is not linked to an employee
        if response.status_code in [403, 404]:
            print(f"✓ Self-service profile update returns {response.status_code} (user not linked to employee) - expected for admin users")
            return
        
        assert response.status_code == 200, f"Expected 200, 403, or 404, got {response.status_code}: {response.text}"
        print("✓ Self-service profile update successful")


class TestNavigationAndIntegration:
    """Tests for navigation and integration between features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_employees" in data
        assert "compliance_score" in data
        print(f"✓ Dashboard stats: {data.get('total_employees')} employees, compliance: {data.get('compliance_score')}%")
    
    def test_copilot_chat(self):
        """Test AI Copilot chat endpoint"""
        response = self.session.post(f"{BASE_URL}/api/copilot/chat", json={
            "message": "What is HMRC RTI?",
            "context": "hmrc"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "response" in data, "Response should contain 'response' field"
        print(f"✓ AI Copilot responded: {data.get('response', '')[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
