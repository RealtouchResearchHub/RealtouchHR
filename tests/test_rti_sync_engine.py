"""
RealtouchHR - RTI Sync Engine API Tests
Tests for the new event-driven RTI Sync Engine with human-in-the-loop approval

Features tested:
- RTI Sync Engine status and configuration
- RTI submissions list
- RTI health check for pay runs
- RTI FPS preparation
- Human-in-the-loop approval workflow (request → approve → submit)
- Immutable audit trails
- HMRC receipts
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "Test123!"


class TestRTISyncStatus:
    """Tests for RTI Sync Engine status endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_rti_sync_status(self):
        """Test GET /api/rti-sync/status - Get RTI Sync Engine status"""
        response = self.session.get(f"{BASE_URL}/api/rti-sync/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "engine_mode" in data, "Response should contain 'engine_mode'"
        assert "company_configured" in data, "Response should contain 'company_configured'"
        assert "settings" in data, "Response should contain 'settings'"
        assert "disclaimers" in data, "Response should contain 'disclaimers'"
        
        # Verify engine mode is valid
        assert data["engine_mode"] in ["sandbox", "live", "paused"], f"Invalid engine mode: {data['engine_mode']}"
        
        # Verify disclaimers are present
        assert "hmrc_alignment" in data["disclaimers"], "Missing HMRC alignment disclaimer"
        assert "employer_responsibility" in data["disclaimers"], "Missing employer responsibility disclaimer"
        assert "submission_approval" in data["disclaimers"], "Missing submission approval disclaimer"
        
        print(f"✓ RTI Sync Status: mode={data['engine_mode']}, configured={data['company_configured']}")


class TestRTISyncSubmissions:
    """Tests for RTI submissions list endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_rti_submissions_list(self):
        """Test GET /api/rti-sync/submissions - List RTI submissions"""
        response = self.session.get(f"{BASE_URL}/api/rti-sync/submissions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "submissions" in data, "Response should contain 'submissions'"
        assert "total" in data, "Response should contain 'total'"
        assert isinstance(data["submissions"], list), "Submissions should be a list"
        
        print(f"✓ RTI Submissions List: {data['total']} submissions found")
        
        # If submissions exist, verify structure
        if data["submissions"]:
            sub = data["submissions"][0]
            assert "submission_id" in sub, "Submission should have 'submission_id'"
            assert "state" in sub or "status" in sub, "Submission should have 'state' or 'status'"
            print(f"  First submission: {sub.get('submission_id')}")


class TestRTIHealthCheck:
    """Tests for RTI health check endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_rti_health_check_nonexistent(self):
        """Test GET /api/rti-sync/health-check/{payrun_id} - Non-existent pay run"""
        response = self.session.get(f"{BASE_URL}/api/rti-sync/health-check/nonexistent_payrun")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ RTI Health Check returns 404 for non-existent pay run")
    
    def test_rti_health_check_existing(self):
        """Test GET /api/rti-sync/health-check/{payrun_id} - Existing pay run"""
        # Get existing pay runs
        runs_response = self.session.get(f"{BASE_URL}/api/payroll/runs")
        if runs_response.status_code != 200 or not runs_response.json():
            pytest.skip("No pay runs available for testing")
        
        payrun_id = runs_response.json()[0].get("payrun_id")
        
        response = self.session.get(f"{BASE_URL}/api/rti-sync/health-check/{payrun_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "payrun_id" in data, "Response should contain 'payrun_id'"
        assert "ready_for_rti" in data, "Response should contain 'ready_for_rti'"
        assert "score" in data, "Response should contain 'score'"
        assert "blocking_issues" in data, "Response should contain 'blocking_issues'"
        assert "recommendation" in data, "Response should contain 'recommendation'"
        
        print(f"✓ RTI Health Check: ready={data['ready_for_rti']}, score={data['score']}")


class TestRTIFullWorkflow:
    """Tests for the full RTI workflow: prepare → request approval → approve → submit"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_rti_prepare_nonexistent_payrun(self):
        """Test POST /api/rti-sync/prepare - Non-existent pay run"""
        response = self.session.post(f"{BASE_URL}/api/rti-sync/prepare", json={
            "payrun_id": "nonexistent_payrun"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ RTI Prepare returns 404 for non-existent pay run")
    
    def test_rti_full_workflow(self):
        """Test full RTI workflow: prepare → request approval → approve → submit"""
        # Step 1: Create a new pay run
        unique_id = uuid.uuid4().hex[:8]
        payrun_response = self.session.post(f"{BASE_URL}/api/payroll/runs", json={
            "period_start": f"2025-02-01",
            "period_end": f"2025-02-28",
            "pay_date": f"2025-02-28"
        })
        
        if payrun_response.status_code != 200:
            pytest.skip(f"Could not create pay run: {payrun_response.text}")
        
        payrun_id = payrun_response.json().get("payrun_id")
        print(f"  Created pay run: {payrun_id}")
        
        # Step 2: Approve the pay run (required for RTI)
        approve_response = self.session.put(f"{BASE_URL}/api/payroll/runs/{payrun_id}", json={
            "status": "approved"
        })
        assert approve_response.status_code == 200, f"Failed to approve pay run: {approve_response.text}"
        print(f"  Pay run approved")
        
        # Step 3: Prepare FPS
        prepare_response = self.session.post(f"{BASE_URL}/api/rti-sync/prepare", json={
            "payrun_id": payrun_id
        })
        
        assert prepare_response.status_code == 200, f"Expected 200, got {prepare_response.status_code}: {prepare_response.text}"
        prepare_data = prepare_response.json()
        
        assert "submission_id" in prepare_data, "Response should contain 'submission_id'"
        assert "validation" in prepare_data, "Response should contain 'validation'"
        
        submission_id = prepare_data["submission_id"]
        print(f"✓ RTI Prepare: submission_id={submission_id}")
        
        # Step 4: Request Approval
        request_approval_response = self.session.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/request-approval"
        )
        
        assert request_approval_response.status_code == 200, f"Expected 200, got {request_approval_response.status_code}: {request_approval_response.text}"
        request_data = request_approval_response.json()
        assert request_data.get("status") == "approval_pending", f"Expected status 'approval_pending', got {request_data.get('status')}"
        print(f"✓ RTI Request Approval: status={request_data.get('status')}")
        
        # Step 5: Approve with confirmation text
        confirmation_text = f"I confirm submission {submission_id}"
        approve_response = self.session.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/approve",
            json={"confirmation_text": confirmation_text}
        )
        
        assert approve_response.status_code == 200, f"Expected 200, got {approve_response.status_code}: {approve_response.text}"
        approve_data = approve_response.json()
        assert approve_data.get("status") == "approved", f"Expected status 'approved', got {approve_data.get('status')}"
        assert approve_data.get("ready_to_submit") == True, "Should be ready to submit"
        print(f"✓ RTI Approve: status={approve_data.get('status')}, mode={approve_data.get('mode')}")
        
        # Step 6: Submit to HMRC
        submit_response = self.session.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/submit",
            json={"acknowledge_disclaimer": True}
        )
        
        assert submit_response.status_code == 200, f"Expected 200, got {submit_response.status_code}: {submit_response.text}"
        submit_data = submit_response.json()
        assert submit_data.get("status") == "submitted", f"Expected status 'submitted', got {submit_data.get('status')}"
        assert "correlation_id" in submit_data, "Response should contain 'correlation_id'"
        print(f"✓ RTI Submit: status={submit_data.get('status')}, correlation_id={submit_data.get('correlation_id')}")
        
        # Step 7: Verify Audit Trail
        audit_response = self.session.get(f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/audit-trail")
        
        assert audit_response.status_code == 200, f"Expected 200, got {audit_response.status_code}: {audit_response.text}"
        audit_data = audit_response.json()
        
        assert "audit_entries" in audit_data, "Response should contain 'audit_entries'"
        assert len(audit_data["audit_entries"]) >= 4, f"Expected at least 4 audit entries, got {len(audit_data['audit_entries'])}"
        
        # Verify immutable entries exist
        immutable_entries = [e for e in audit_data["audit_entries"] if e.get("immutable")]
        assert len(immutable_entries) >= 2, f"Expected at least 2 immutable entries, got {len(immutable_entries)}"
        print(f"✓ RTI Audit Trail: {len(audit_data['audit_entries'])} entries, {len(immutable_entries)} immutable")


class TestRTIApprovalValidation:
    """Tests for RTI approval validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_approve_wrong_confirmation(self):
        """Test approval with wrong confirmation text"""
        # Get existing submissions
        subs_response = self.session.get(f"{BASE_URL}/api/rti-sync/submissions")
        if subs_response.status_code != 200:
            pytest.skip("Could not get submissions")
        
        subs = subs_response.json().get("submissions", [])
        pending_sub = next((s for s in subs if s.get("state") == "approval_pending"), None)
        
        if not pending_sub:
            # Create a new submission for testing
            runs_response = self.session.get(f"{BASE_URL}/api/payroll/runs")
            if runs_response.status_code != 200 or not runs_response.json():
                pytest.skip("No pay runs available")
            
            # Find an approved pay run without existing submission
            approved_runs = [r for r in runs_response.json() if r.get("status") == "approved"]
            if not approved_runs:
                pytest.skip("No approved pay runs available")
            
            # Try to prepare a new submission
            prepare_response = self.session.post(f"{BASE_URL}/api/rti-sync/prepare", json={
                "payrun_id": approved_runs[0]["payrun_id"]
            })
            
            if prepare_response.status_code != 200:
                pytest.skip("Could not prepare submission for testing")
            
            submission_id = prepare_response.json().get("submission_id")
            
            # Request approval
            self.session.post(f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/request-approval")
        else:
            submission_id = pending_sub.get("submission_id")
        
        # Try to approve with wrong confirmation
        response = self.session.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/approve",
            json={"confirmation_text": "wrong confirmation text"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ RTI Approve rejects wrong confirmation text")
    
    def test_submit_without_disclaimer(self):
        """Test submission without acknowledging disclaimer"""
        # Get existing approved submissions
        subs_response = self.session.get(f"{BASE_URL}/api/rti-sync/submissions")
        if subs_response.status_code != 200:
            pytest.skip("Could not get submissions")
        
        subs = subs_response.json().get("submissions", [])
        approved_sub = next((s for s in subs if s.get("state") == "approved"), None)
        
        if not approved_sub:
            pytest.skip("No approved submissions available for testing")
        
        submission_id = approved_sub.get("submission_id")
        
        # Try to submit without disclaimer
        response = self.session.post(
            f"{BASE_URL}/api/rti-sync/submissions/{submission_id}/submit",
            json={"acknowledge_disclaimer": False}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ RTI Submit rejects without disclaimer acknowledgment")


class TestRTIReceipts:
    """Tests for RTI receipts endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
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
    
    def test_rti_receipts_list(self):
        """Test GET /api/rti-sync/receipts - List HMRC receipts"""
        response = self.session.get(f"{BASE_URL}/api/rti-sync/receipts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "receipts" in data, "Response should contain 'receipts'"
        assert "total" in data, "Response should contain 'total'"
        assert isinstance(data["receipts"], list), "Receipts should be a list"
        
        print(f"✓ RTI Receipts List: {data['total']} receipts found")
        
        # If receipts exist, verify structure
        if data["receipts"]:
            receipt = data["receipts"][0]
            assert "receipt_id" in receipt, "Receipt should have 'receipt_id'"
            assert "correlation_id" in receipt, "Receipt should have 'correlation_id'"
            assert "mode" in receipt, "Receipt should have 'mode'"
            print(f"  First receipt: {receipt.get('receipt_id')}, mode={receipt.get('mode')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
