import requests
import sys
import json
from datetime import datetime, timedelta

class RealtouchHRTester:
    def __init__(self, base_url="https://realtouch-comply.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.company_id = None
        self.employee_id = None
        self.payrun_id = None  # Add payrun_id for export tests
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_health_check(self):
        """Test basic health endpoints"""
        print("\n=== HEALTH CHECK TESTS ===")
        self.run_test("Root endpoint", "GET", "", 200)
        self.run_test("Health check", "GET", "health", 200)

    def test_registration(self):
        """Test user registration"""
        print("\n=== REGISTRATION TESTS ===")
        timestamp = int(datetime.now().timestamp())
        test_data = {
            "email": f"test.user.{timestamp}@example.com",
            "password": "TestPass123!",
            "name": "Test User",
            "company_name": "Test Company Ltd"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_data
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['user_id']
            self.company_id = response['user'].get('company_id')
            print(f"   Token: {self.token[:20]}...")
            print(f"   User ID: {self.user_id}")
            print(f"   Company ID: {self.company_id}")
            return True
        return False

    def test_login(self):
        """Test user login with existing credentials"""
        print("\n=== LOGIN TESTS ===")
        # Try to login with the registered user
        if not self.user_id:
            print("⚠️  Skipping login test - no registered user")
            return False
            
        # For testing, we'll use the token from registration
        success, response = self.run_test(
            "Get current user",
            "GET", 
            "auth/me",
            200
        )
        return success

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        print("\n=== DASHBOARD TESTS ===")
        return self.run_test(
            "Dashboard stats",
            "GET",
            "dashboard/stats",
            200
        )[0]

    def test_company_operations(self):
        """Test company-related operations"""
        print("\n=== COMPANY TESTS ===")
        
        # Get company
        success, company = self.run_test(
            "Get company",
            "GET",
            "company",
            200
        )
        
        if success and company:
            # Update company
            update_data = {
                "industry": "Technology",
                "size": "10-50",
                "setup_completed": True
            }
            self.run_test(
                "Update company",
                "PUT",
                "company",
                200,
                data=update_data
            )
        
        return success

    def test_employee_operations(self):
        """Test employee CRUD operations"""
        print("\n=== EMPLOYEE TESTS ===")
        
        # Create employee
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john.doe.{int(datetime.now().timestamp())}@example.com",
            "job_title": "Software Developer",
            "department": "Engineering",
            "salary": 45000,
            "ni_number": "AB123456C",
            "tax_code": "1257L"
        }
        
        success, response = self.run_test(
            "Create employee",
            "POST",
            "employees",
            200,
            data=employee_data
        )
        
        if success and 'employee_id' in response:
            self.employee_id = response['employee_id']
            print(f"   Employee ID: {self.employee_id}")
            
            # Get employees list
            self.run_test(
                "Get employees list",
                "GET",
                "employees",
                200
            )
            
            # Get specific employee
            self.run_test(
                "Get specific employee",
                "GET",
                f"employees/{self.employee_id}",
                200
            )
            
            # Update employee
            update_data = {
                "bank_account": "12345678",
                "bank_sort_code": "12-34-56"
            }
            self.run_test(
                "Update employee",
                "PUT",
                f"employees/{self.employee_id}",
                200,
                data=update_data
            )
            
            return True
        
        return False

    def test_leave_operations(self):
        """Test leave request operations"""
        print("\n=== LEAVE TESTS ===")
        
        # Create leave request
        leave_data = {
            "leave_type": "annual",
            "start_date": "2024-12-20",
            "end_date": "2024-12-22",
            "reason": "Christmas holiday"
        }
        
        success, response = self.run_test(
            "Create leave request",
            "POST",
            "leave",
            200,
            data=leave_data
        )
        
        if success and 'leave_id' in response:
            leave_id = response['leave_id']
            
            # Get leave requests
            self.run_test(
                "Get leave requests",
                "GET",
                "leave",
                200
            )
            
            # Approve leave request
            self.run_test(
                "Approve leave request",
                "PUT",
                f"leave/{leave_id}",
                200,
                data={"status": "approved"}
            )
            
            return True
        
        return False

    def test_document_operations(self):
        """Test document operations"""
        print("\n=== DOCUMENT TESTS ===")
        
        # Create document
        doc_data = {
            "name": "Employee Handbook",
            "doc_type": "policy",
            "content": "This is the employee handbook content...",
            "employee_id": self.employee_id
        }
        
        success, response = self.run_test(
            "Create document",
            "POST",
            "documents",
            200,
            data=doc_data
        )
        
        if success:
            # Get documents
            self.run_test(
                "Get documents",
                "GET",
                "documents",
                200
            )
            return True
        
        return False

    def test_shift_operations(self):
        """Test shift/rota operations"""
        print("\n=== SHIFT/ROTA TESTS ===")
        
        if not self.employee_id:
            print("⚠️  Skipping shift tests - no employee created")
            return False
        
        # Create shift
        shift_data = {
            "employee_id": self.employee_id,
            "date": "2024-12-16",
            "start_time": "09:00",
            "end_time": "17:00",
            "break_minutes": 60
        }
        
        success, response = self.run_test(
            "Create shift",
            "POST",
            "shifts",
            200,
            data=shift_data
        )
        
        if success and 'shift_id' in response:
            shift_id = response['shift_id']
            
            # Get shifts
            self.run_test(
                "Get shifts",
                "GET",
                "shifts",
                200
            )
            
            # Clock in
            self.run_test(
                "Clock in",
                "POST",
                f"shifts/{shift_id}/clock-in",
                200
            )
            
            # Clock out
            self.run_test(
                "Clock out",
                "POST",
                f"shifts/{shift_id}/clock-out",
                200
            )
            
            return True
        
        return False

    def test_payroll_operations(self):
        """Test payroll operations"""
        print("\n=== PAYROLL TESTS ===")
        
        # Create pay run
        payrun_data = {
            "period_start": "2024-12-01",
            "period_end": "2024-12-31",
            "pay_date": "2024-12-31"
        }
        
        success, response = self.run_test(
            "Create pay run",
            "POST",
            "payroll/runs",
            200,
            data=payrun_data
        )
        
        if success and 'payrun_id' in response:
            payrun_id = response['payrun_id']
            self.payrun_id = payrun_id  # Store for export tests
            
            # Get pay runs
            self.run_test(
                "Get pay runs",
                "GET",
                "payroll/runs",
                200
            )
            
            # Get specific pay run
            self.run_test(
                "Get specific pay run",
                "GET",
                f"payroll/runs/{payrun_id}",
                200
            )
            
            # Get payslips
            self.run_test(
                "Get payslips",
                "GET",
                f"payroll/runs/{payrun_id}/payslips",
                200
            )
            
            return True
        
        return False

    def test_audit_operations(self):
        """Test audit log operations"""
        print("\n=== AUDIT TESTS ===")
        
        return self.run_test(
            "Get audit log",
            "GET",
            "audit",
            200
        )[0]

    def test_compliance_operations(self):
        """Test compliance operations"""
        print("\n=== COMPLIANCE TESTS ===")
        
        # Get compliance tasks
        success1 = self.run_test(
            "Get compliance tasks",
            "GET",
            "compliance/tasks",
            200
        )[0]
        
        # Get compliance score
        success2 = self.run_test(
            "Get compliance score",
            "GET",
            "compliance/score",
            200
        )[0]
        
        return success1 and success2

    def test_ai_copilot(self):
        """Test AI Copilot functionality"""
        print("\n=== AI COPILOT TESTS ===")
        
        copilot_data = {
            "message": "What are the key compliance requirements for UK payroll?",
            "context": "payroll_guidance"
        }
        
        return self.run_test(
            "AI Copilot chat",
            "POST",
            "copilot/chat",
            200,
            data=copilot_data
        )[0]

    def test_notifications(self):
        """Test notification operations"""
        print("\n=== NOTIFICATION TESTS ===")
        
        # Get notifications
        success1 = self.run_test(
            "Get notifications",
            "GET",
            "notifications",
            200
        )[0]
        
        # Mark all notifications as read
        success2 = self.run_test(
            "Mark all notifications read",
            "PUT",
            "notifications/read-all",
            200
        )[0]
        
        return success1 and success2

    def test_bulk_import(self):
        """Test bulk import functionality"""
        print("\n=== BULK IMPORT TESTS ===")
        
        # Get employee import template
        success = self.run_test(
            "Get employee import template",
            "GET",
            "employees/import/template",
            200
        )[0]
        
        return success

    def test_payroll_exports(self):
        """Test payroll PDF and HMRC exports"""
        print("\n=== PAYROLL EXPORT TESTS ===")
        
        if not hasattr(self, 'payrun_id') or not self.payrun_id:
            print("⚠️  Skipping export tests - no payrun created")
            return False
            
        if not self.employee_id:
            print("⚠️  Skipping export tests - no employee created")
            return False
        
        # Test PDF payslip download
        success1 = self.run_test(
            "Download payslip PDF",
            "GET",
            f"payroll/runs/{self.payrun_id}/payslips/{self.employee_id}/pdf",
            200
        )[0]
        
        # Test HMRC exports
        success2 = self.run_test(
            "Export FPS",
            "GET",
            f"payroll/runs/{self.payrun_id}/export/fps",
            200
        )[0]
        
        success3 = self.run_test(
            "Export EPS", 
            "GET",
            f"payroll/runs/{self.payrun_id}/export/eps",
            200
        )[0]
        
        success4 = self.run_test(
            "Export P32",
            "GET",
            f"payroll/runs/{self.payrun_id}/export/p32",
            200
        )[0]
        
        return success1 and success2 and success3 and success4

    def test_onboarding(self):
        """Test onboarding wizard endpoints"""
        print("\n=== ONBOARDING TESTS ===")
        
        # Get onboarding progress
        success1 = self.run_test(
            "Get onboarding progress",
            "GET",
            "onboarding/progress",
            200
        )[0]
        
        # Test quick employee creation
        employee_data = {
            "first_name": "Quick",
            "last_name": "Employee",
            "email": f"quick.employee.{int(datetime.now().timestamp())}@example.com",
            "job_title": "Test Role",
            "salary": 30000
        }
        
        success2 = self.run_test(
            "Quick employee creation",
            "POST",
            "onboarding/quick-employee",
            200,
            data=employee_data
        )[0]
        
        # Test quick payrun creation
        success3 = self.run_test(
            "Quick payrun creation",
            "POST",
            "onboarding/quick-payrun",
            200
        )[0]
        
        return success1 and success2 and success3

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting RealtouchHR API Test Suite")
        print(f"Testing against: {self.base_url}")
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Registration", self.test_registration),
            ("Authentication", self.test_login),
            ("Dashboard", self.test_dashboard_stats),
            ("Company Operations", self.test_company_operations),
            ("Employee Operations", self.test_employee_operations),
            ("Leave Operations", self.test_leave_operations),
            ("Document Operations", self.test_document_operations),
            ("Shift Operations", self.test_shift_operations),
            ("Payroll Operations", self.test_payroll_operations),
            ("Audit Operations", self.test_audit_operations),
            ("Compliance Operations", self.test_compliance_operations),
            ("AI Copilot", self.test_ai_copilot)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.failed_tests.append({
                    "test": test_name,
                    "error": str(e)
                })

        # Print results
        print(f"\n📊 Test Results:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"  - {failure.get('test', 'Unknown')}: {failure.get('error', failure.get('response', 'Unknown error'))}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = RealtouchHRTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())