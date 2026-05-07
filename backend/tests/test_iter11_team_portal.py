"""Iter11 backend tests: Team Management + Stripe Customer Portal"""
import os, uuid, pytest, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    fe_env = Path(__file__).resolve().parents[2] / 'frontend' / '.env'
    for line in fe_env.read_text().splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def owner():
    """Get an owner via sandbox demo endpoint (no auth)."""
    r = requests.post(f"{API}/demo/sandbox", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("token") or data.get("session_token")
    assert token
    return {"token": token, "user": data.get("user", {}), "headers": {"Authorization": f"Bearer {token}"}}


# ---------- Team Management ----------

class TestTeamManagement:
    def test_list_users(self, owner):
        r = requests.get(f"{API}/users", headers=owner["headers"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert "users" in body and isinstance(body["users"], list)
        assert body["total"] >= 1

    def test_invite_requires_auth(self):
        r = requests.post(f"{API}/users/invite", json={"email": "x@y.com", "name": "X", "role": "hr_manager"})
        assert r.status_code == 401

    def test_invite_rejects_invalid_role(self, owner):
        r = requests.post(f"{API}/users/invite", headers=owner["headers"],
                          json={"email": f"bad_{uuid.uuid4().hex[:6]}@test.com", "name": "Bad", "role": "owner"})
        assert r.status_code == 400

    def test_invite_rejects_unknown_role(self, owner):
        r = requests.post(f"{API}/users/invite", headers=owner["headers"],
                          json={"email": f"bad2_{uuid.uuid4().hex[:6]}@test.com", "name": "Bad", "role": "superuser"})
        assert r.status_code == 400

    def test_full_invite_flow(self, owner):
        email = f"TEST_invitee_{uuid.uuid4().hex[:8]}@example.com"
        # 1) create invite
        r = requests.post(f"{API}/users/invite", headers=owner["headers"],
                          json={"email": email, "name": "Invited User", "role": "hr_manager"})
        assert r.status_code == 200, r.text
        inv = r.json()
        assert "invite_link" in inv and "/invite/" in inv["invite_link"]
        assert inv.get("expires_at")
        invite_id = inv["invite_id"]
        token = inv["invite_link"].rsplit("/", 1)[-1]

        # 2) duplicate invite blocked
        r2 = requests.post(f"{API}/users/invite", headers=owner["headers"],
                           json={"email": email, "name": "Invited User", "role": "hr_manager"})
        assert r2.status_code == 400

        # 3) list invites (admin+)
        r3 = requests.get(f"{API}/users/invites", headers=owner["headers"])
        assert r3.status_code == 200
        assert any(i["invite_id"] == invite_id for i in r3.json()["invites"])

        # 4) public preview (no auth)
        r4 = requests.get(f"{API}/users/invite/{token}")
        assert r4.status_code == 200, r4.text
        prev = r4.json()
        assert prev["email"] == email
        assert prev["role"] == "hr_manager"
        assert "company_name" in prev

        # 5) invalid preview token -> 404
        r5 = requests.get(f"{API}/users/invite/bogus-token-xyz")
        assert r5.status_code == 404

        # 6) accept with short password -> 422 (pydantic)
        r6 = requests.post(f"{API}/users/invite/accept", json={"invite_token": token, "password": "short"})
        assert r6.status_code == 422

        # 7) accept with valid password (no auth) -> 200 + JWT
        r7 = requests.post(f"{API}/users/invite/accept", json={"invite_token": token, "password": "StrongPass123!"})
        assert r7.status_code == 200, r7.text
        acc = r7.json()
        assert "token" in acc and acc["user"]["role"] == "hr_manager"
        assert acc["user"]["email"] == email
        new_headers = {"Authorization": f"Bearer {acc['token']}"}

        # 8) accepting same token again -> 404 (status=accepted)
        r8 = requests.post(f"{API}/users/invite/accept", json={"invite_token": token, "password": "StrongPass123!"})
        assert r8.status_code == 404

        # 9) new hr_manager user can NOT invite (requires admin+)
        r9 = requests.post(f"{API}/users/invite", headers=new_headers,
                           json={"email": f"TEST_{uuid.uuid4().hex[:6]}@x.com", "name": "X", "role": "viewer"})
        assert r9.status_code == 403

        # 10) hr_manager cannot change roles (owner only)
        new_user_id = acc["user"]["user_id"]
        r10 = requests.put(f"{API}/users/{new_user_id}/role", headers=new_headers, json={"role": "admin"})
        assert r10.status_code == 403

        # 11) owner changes new user role to admin
        r11 = requests.put(f"{API}/users/{new_user_id}/role", headers=owner["headers"], json={"role": "admin"})
        assert r11.status_code == 200

        # 12) owner cannot demote self
        owner_uid = owner["user"].get("user_id")
        if owner_uid:
            r12 = requests.put(f"{API}/users/{owner_uid}/role", headers=owner["headers"], json={"role": "admin"})
            assert r12.status_code == 400

        # 13) owner removes the user
        r13 = requests.delete(f"{API}/users/{new_user_id}", headers=owner["headers"])
        assert r13.status_code == 200

        # 14) removed user's token is now invalid (session deleted)
        r14 = requests.get(f"{API}/users", headers=new_headers)
        assert r14.status_code == 401

    def test_revoke_invite(self, owner):
        email = f"TEST_revoke_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/users/invite", headers=owner["headers"],
                          json={"email": email, "name": "Revokee", "role": "viewer"})
        assert r.status_code == 200
        invite_id = r.json()["invite_id"]
        r2 = requests.delete(f"{API}/users/invites/{invite_id}", headers=owner["headers"])
        assert r2.status_code == 200
        # revoking again -> 404 (no pending invite with that id)
        r3 = requests.delete(f"{API}/users/invites/{invite_id}", headers=owner["headers"])
        assert r3.status_code == 404


# ---------- Stripe Customer Portal ----------

class TestStripePortal:
    def test_portal_requires_owner(self, owner):
        # Fresh sandbox has no completed checkout → expected 400 "No Stripe customer found"
        r = requests.post(f"{API}/payments/portal", headers=owner["headers"],
                          json={"return_url": "https://example.com/billing"})
        assert r.status_code == 400, r.text
        assert "stripe customer" in r.json().get("detail", "").lower()

    def test_portal_requires_auth(self):
        r = requests.post(f"{API}/payments/portal", json={"return_url": "https://example.com/billing"})
        assert r.status_code == 401


# ---------- Smoke regression ----------

class TestRegressionSmoke:
    def test_plans_reachable(self, owner):
        r = requests.get(f"{API}/payments/plans", headers=owner["headers"])
        assert r.status_code == 200
        assert "plans" in r.json()

    def test_billing_info_owner(self, owner):
        r = requests.get(f"{API}/payments/billing", headers=owner["headers"])
        assert r.status_code == 200

    def test_dashboard_stats(self, owner):
        r = requests.get(f"{API}/dashboard/stats", headers=owner["headers"])
        assert r.status_code == 200
        assert "total_employees" in r.json()

    def test_audit_log(self, owner):
        r = requests.get(f"{API}/audit", headers=owner["headers"])
        assert r.status_code == 200
