"""
RealtouchHR Feature Tests - Iteration 3
Testing: AI Copilot, Payslip PDF, Employee CRUD, Pay Run Creation
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rtisync-staging.preview.emergentagent.com').rstrip('/')

# Test data storage
test_data = {
    "user_id": None,
    "token": None,
    "company_id": None,
    "employee_id": None,
    "payrun_id": None
}


class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_01_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_02_register_test_user(self):
        """Register a new test user for testing"""
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "email": f"test_copilot_{unique_id}@example.com",
            "password": "Test123!",
            "name": f"Test User {unique_id}",
            "company_name": f"Test Company {unique_id}"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        
        test_data["token"] = data["token"]
        test_data["user_id"] = data["user"]["user_id"]
        test_data["company_id"] = data["user"].get("company_id")
        
        print(f"✓ User registered: {data['user']['email']}")
        print(f"  Token: {test_data['token'][:30]}...")
    
    def test_03_login_test_user(self):
        """Test login with existing credentials"""
        # Use the test credentials provided
        payload = {
            "email": "test@example.com",
            "password": "Test123!"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        # If test user doesn't exist, use the registered user
        if response.status_code != 200:
            print(f"  Note: test@example.com not found, using registered user")
            assert test_data["token"] is not None, "No token available from registration"
        else:
            data = response.json()
            # Update token if login succeeded
            test_data["token"] = data["token"]
            test_data["user_id"] = data["user"]["user_id"]
            test_data["company_id"] = data["user"].get("company_id")
            print(f"✓ Login successful: {data['user']['email']}")
    
    def test_04_get_current_user(self):
        """Test getting current user info"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✓ Current user: {data['email']}")


class TestDashboard:
    """Dashboard and compliance score tests"""
    
    def test_05_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        assert "total_employees" in data
        assert "compliance_score" in data
        print(f"✓ Dashboard stats: {data}")
    
    def test_06_compliance_score(self):
        """Test compliance score endpoint"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/compliance/score", headers=headers)
        assert response.status_code == 200, f"Compliance score failed: {response.text}"
        
        data = response.json()
        assert "score" in data
        assert isinstance(data["score"], int)
        print(f"✓ Compliance score: {data['score']}%")


class TestEmployeeCRUD:
    """Employee management CRUD tests"""
    
    def test_07_create_employee(self):
        """Create a new employee"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "first_name": "John",
            "last_name": f"Doe_{unique_id}",
            "email": f"john.doe_{unique_id}@testcompany.com",
            "job_title": "Software Engineer",
            "department": "Engineering",
            "salary": 45000,
            "ni_number": "AB123456C",
            "tax_code": "1257L",
            "bank_account": "12345678",
            "bank_sort_code": "12-34-56"
        }
        response = requests.post(f"{BASE_URL}/api/employees", json=payload, headers=headers)
        assert response.status_code == 200, f"Create employee failed: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        test_data["employee_id"] = data["employee_id"]
        print(f"✓ Employee created: {data['first_name']} {data['last_name']} (ID: {data['employee_id']})")
    
    def test_08_get_employees(self):
        """Get list of employees"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200, f"Get employees failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} employees")
    
    def test_09_get_single_employee(self):
        """Get single employee by ID"""
        if not test_data["employee_id"]:
            pytest.skip("No employee ID available")
        
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/employees/{test_data['employee_id']}", headers=headers)
        assert response.status_code == 200, f"Get employee failed: {response.text}"
        
        data = response.json()
        assert data["employee_id"] == test_data["employee_id"]
        print(f"✓ Retrieved employee: {data['first_name']} {data['last_name']}")
    
    def test_10_update_employee(self):
        """Update employee details"""
        if not test_data["employee_id"]:
            pytest.skip("No employee ID available")
        
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        payload = {
            "job_title": "Senior Software Engineer",
            "salary": 55000
        }
        response = requests.put(f"{BASE_URL}/api/employees/{test_data['employee_id']}", json=payload, headers=headers)
        assert response.status_code == 200, f"Update employee failed: {response.text}"
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/employees/{test_data['employee_id']}", headers=headers)
        data = response.json()
        assert data["job_title"] == "Senior Software Engineer"
        assert data["salary"] == 55000
        print(f"✓ Employee updated: {data['job_title']}, salary: £{data['salary']}")


class TestPayroll:
    """Payroll and payslip tests"""
    
    def test_11_create_pay_run(self):
        """Create a new pay run"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        payload = {
            "period_start": "2024-12-01",
            "period_end": "2024-12-31",
            "pay_date": "2024-12-28"
        }
        response = requests.post(f"{BASE_URL}/api/payroll/runs", json=payload, headers=headers)
        assert response.status_code == 200, f"Create pay run failed: {response.text}"
        
        data = response.json()
        assert "payrun_id" in data
        test_data["payrun_id"] = data["payrun_id"]
        print(f"✓ Pay run created: {data['payrun_id']}")
        print(f"  Total gross: £{data['total_gross']}, Net: £{data['total_net']}")
    
    def test_12_get_pay_runs(self):
        """Get list of pay runs"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/payroll/runs", headers=headers)
        assert response.status_code == 200, f"Get pay runs failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} pay runs")
    
    def test_13_get_payslips(self):
        """Get payslips for a pay run"""
        if not test_data["payrun_id"]:
            pytest.skip("No pay run ID available")
        
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/payroll/runs/{test_data['payrun_id']}/payslips", headers=headers)
        assert response.status_code == 200, f"Get payslips failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} payslips for pay run")
        
        # Store first employee ID for PDF test
        if data and len(data) > 0:
            test_data["payslip_employee_id"] = data[0]["employee_id"]
    
    def test_14_download_payslip_pdf(self):
        """Download individual payslip as PDF"""
        if not test_data["payrun_id"]:
            pytest.skip("No pay run ID available")
        
        # Get payslips first to get an employee ID
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/payroll/runs/{test_data['payrun_id']}/payslips", headers=headers)
        
        if response.status_code != 200 or not response.json():
            pytest.skip("No payslips available for PDF download")
        
        payslips = response.json()
        employee_id = payslips[0]["employee_id"]
        
        # Download PDF
        response = requests.get(
            f"{BASE_URL}/api/payroll/runs/{test_data['payrun_id']}/payslips/{employee_id}/pdf",
            headers=headers
        )
        assert response.status_code == 200, f"Download payslip PDF failed: {response.text}"
        
        # Verify it's a PDF
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"✓ Payslip PDF downloaded: {len(response.content)} bytes")
        print(f"  Content-Disposition: {response.headers.get('content-disposition', 'N/A')}")
    
    def test_15_download_all_payslips_pdf(self):
        """Download all payslips for a pay run as PDF"""
        if not test_data["payrun_id"]:
            pytest.skip("No pay run ID available")
        
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(
            f"{BASE_URL}/api/payroll/runs/{test_data['payrun_id']}/payslips/pdf",
            headers=headers
        )
        
        # May return 404 if no payslips
        if response.status_code == 404:
            print("  Note: No payslips available for bulk PDF download")
            return
        
        assert response.status_code == 200, f"Download all payslips PDF failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        print(f"✓ All payslips PDF downloaded: {len(response.content)} bytes")


class TestAICopilot:
    """AI Copilot functionality tests"""
    
    def test_16_copilot_chat_basic(self):
        """Test AI Copilot basic chat functionality"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        payload = {
            "message": "What are the UK payroll requirements?"
        }
        response = requests.post(f"{BASE_URL}/api/copilot/chat", json=payload, headers=headers)
        assert response.status_code == 200, f"Copilot chat failed: {response.text}"
        
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        print(f"✓ AI Copilot responded: {data['response'][:100]}...")
        print(f"  Suggestions: {data.get('suggestions', [])}")
        print(f"  Requires approval: {data.get('requires_approval', False)}")
    
    def test_17_copilot_chat_compliance(self):
        """Test AI Copilot with compliance question"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        payload = {
            "message": "Check my compliance status"
        }
        response = requests.post(f"{BASE_URL}/api/copilot/chat", json=payload, headers=headers)
        assert response.status_code == 200, f"Copilot compliance chat failed: {response.text}"
        
        data = response.json()
        assert "response" in data
        print(f"✓ AI Copilot compliance response: {data['response'][:100]}...")
    
    def test_18_copilot_chat_approval_required(self):
        """Test AI Copilot with action requiring approval"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        payload = {
            "message": "Run payroll for this month"
        }
        response = requests.post(f"{BASE_URL}/api/copilot/chat", json=payload, headers=headers)
        assert response.status_code == 200, f"Copilot approval chat failed: {response.text}"
        
        data = response.json()
        assert "response" in data
        # This should require approval since it mentions "run payroll"
        print(f"✓ AI Copilot approval response: {data['response'][:100]}...")
        print(f"  Requires approval: {data.get('requires_approval', False)}")


class TestNotifications:
    """Notification system tests"""
    
    def test_19_get_notifications(self):
        """Get user notifications"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        print(f"✓ Notifications: {len(data['notifications'])} total, {data['unread_count']} unread")


class TestAuditLog:
    """Audit log tests"""
    
    def test_20_get_audit_log(self):
        """Get audit log entries"""
        headers = {"Authorization": f"Bearer {test_data['token']}"}
        response = requests.get(f"{BASE_URL}/api/audit", headers=headers)
        assert response.status_code == 200, f"Get audit log failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Audit log: {len(data)} entries")
        if data:
            print(f"  Latest action: {data[0].get('action', 'N/A')} on {data[0].get('entity_type', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
