"""
Iteration 15 — Compliance Trust Badge + Pricing change tests
- Pricing: GET /api/payments/plans returns starter=£39, pro=£59, enterprise=£149
- Trust badge owner view: GET /api/trust-badge/me
- Trust badge public verify (JSON): GET /api/trust-badge/{badge_id}/verify
- Trust badge SVG: GET /api/trust-badge/{badge_id}/badge.svg
- Trust badge HTML verification page: GET /api/trust-badge/{badge_id}/page
- Tier escalation via 2FA enable
- Deterministic / non-guessable badge_id
- Regression: /api/auth/me, /api/company, /api/employees
"""
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ukvi-staging.preview.emergentagent.com").rstrip("/")


# ------------- shared fixtures (override conftest to register a fresh user with company) -------------

@pytest.fixture(scope="module")
def fresh_user():
    """Register a fresh owner user with company so trust badge endpoints have data."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_iter15_{suffix}@example.com"
    password = "Test123!"
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": password,
        "name": "Iter15 Tester",
        "company_name": f"TEST_Iter15Co_{suffix}",
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token, "no token returned"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return {"session": s, "email": email, "password": password, "token": token, "suffix": suffix}


@pytest.fixture(scope="module")
def fallback_existing_session():
    """Login the existing test@example.com if available — used for some regression checks."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "test@example.com", "password": "Test123!"})
    if r.status_code == 200:
        s.headers.update({"Authorization": f"Bearer {r.json().get('token')}"})
        return s
    return None


# ============================= PRICING =============================

class TestPricing:
    def test_plans_endpoint_pricing(self, fresh_user):
        s = fresh_user["session"]
        r = s.get(f"{BASE_URL}/api/payments/plans")
        assert r.status_code == 200, r.text
        data = r.json()
        # Spec: response wraps plans dict
        plans = data.get("plans") or data
        assert "starter" in plans and "professional" in plans and "enterprise" in plans
        assert float(plans["starter"]["price"]) == 39.00, f"starter price={plans['starter']['price']}"
        assert float(plans["professional"]["price"]) == 59.00, f"pro price={plans['professional']['price']}"
        assert float(plans["enterprise"]["price"]) == 149.00, f"enterprise price={plans['enterprise']['price']}"
        # currency check
        assert plans["starter"]["currency"].lower() == "gbp"


# ============================= TRUST BADGE — OWNER VIEW =============================

class TestTrustBadgeOwner:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/trust-badge/me")
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_owner_view_returns_badge(self, fresh_user):
        s = fresh_user["session"]
        r = s.get(f"{BASE_URL}/api/trust-badge/me")
        assert r.status_code == 200, r.text
        data = r.json()
        # core fields
        assert data.get("badge_id", "").startswith("rthr-"), f"badge_id={data.get('badge_id')}"
        assert data.get("verified_level") in ("bronze", "silver", "gold")
        assert data.get("verify_url") and "/trust/" in data["verify_url"]
        assert data.get("badge_svg_url") and "/badge.svg" in data["badge_svg_url"]
        assert "<a " in (data.get("embed_html") or "") and "<img" in data["embed_html"]
        assert "![" in (data.get("embed_markdown") or "")
        # CRITICAL (iter-15 retest fix): all badge URLs must use the public REACT_APP_BACKEND_URL
        public_host = BASE_URL  # already from REACT_APP_BACKEND_URL
        assert data["badge_svg_url"].startswith(public_host), \
            f"badge_svg_url leaks internal host: {data['badge_svg_url']} (expected prefix {public_host})"
        assert data["verify_url"].startswith(public_host), \
            f"verify_url leaks internal host: {data['verify_url']}"
        assert public_host in data["embed_html"], \
            f"embed_html missing public host: {data['embed_html']}"
        assert public_host in data["embed_markdown"], \
            f"embed_markdown missing public host: {data['embed_markdown']}"
        # And it MUST NOT contain the internal 378af53a- preview hostname
        assert "378af53a" not in data["badge_svg_url"], "internal hostname leaked in badge_svg_url"
        assert "378af53a" not in data["embed_html"], "internal hostname leaked in embed_html"
        att = data.get("attestations") or {}
        for k in ("gdpr_compliant", "owner_2fa_enabled", "audit_logged",
                  "subscription_active", "hmrc_rti_configured",
                  "ukvi_sponsor_licence", "pension_auto_enrolment"):
            assert k in att, f"missing attestation key {k}"
        # save to module state via the fixture's dict
        fresh_user["badge_id"] = data["badge_id"]
        fresh_user["initial_level"] = data["verified_level"]
        fresh_user["initial_owner_2fa"] = att.get("owner_2fa_enabled")

    def test_no_company_returns_400(self):
        """Register user without company_name -> /trust-badge/me should 400."""
        suffix = uuid.uuid4().hex[:8]
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_iter15_nocomp_{suffix}@example.com",
            "password": "Test123!",
            "name": "No Company"
            # intentionally no company_name
        })
        if r.status_code not in (200, 201):
            pytest.skip(f"register without company not supported: {r.status_code} {r.text[:120]}")
        tok = r.json().get("token")
        if not tok:
            pytest.skip("no token in register response")
        s.headers.update({"Authorization": f"Bearer {tok}"})
        # check current user
        me = s.get(f"{BASE_URL}/api/auth/me")
        if me.status_code == 200 and me.json().get("company_id"):
            pytest.skip("registration auto-created company; can't test 400 path")
        r2 = s.get(f"{BASE_URL}/api/trust-badge/me")
        assert r2.status_code == 400, f"expected 400 with no company, got {r2.status_code}"


# ============================= TRUST BADGE — PUBLIC VERIFY (JSON) =============================

class TestPublicVerify:
    def test_verify_ok_no_auth(self, fresh_user):
        badge_id = fresh_user.get("badge_id")
        assert badge_id, "previous test should have populated badge_id"
        # raw requests (no auth header)
        r = requests.get(f"{BASE_URL}/api/trust-badge/{badge_id}/verify")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("valid") is True
        assert data.get("verified_level") in ("bronze", "silver", "gold")
        assert data.get("company_name")
        assert isinstance(data.get("attestations"), dict)
        platform = data.get("platform") or {}
        regs = platform.get("regulator_alignment")
        assert isinstance(regs, list) and len(regs) >= 3
        joined = " ".join(regs)
        assert "GDPR" in joined and "HMRC" in joined

    def test_verify_invalid_badge_404(self):
        r = requests.get(f"{BASE_URL}/api/trust-badge/rthr-deadbeefdeadbeef/verify")
        assert r.status_code == 404


# ============================= TRUST BADGE — SVG =============================

class TestBadgeSVG:
    def test_svg_returns_image(self, fresh_user):
        badge_id = fresh_user["badge_id"]
        r = requests.get(f"{BASE_URL}/api/trust-badge/{badge_id}/badge.svg")
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "image/svg+xml" in ct, f"content-type={ct}"
        body = r.text
        assert "<svg" in body and "</svg>" in body
        # company name should appear (or escaped)
        comp = (fresh_user.get("session").get(f"{BASE_URL}/api/auth/me").json() or {}).get("company_name") or ""
        # we may not have it directly — at least check tier label
        assert any(tier in body for tier in ("BRONZE", "SILVER", "GOLD"))

    def test_svg_invalid_returns_404_with_invalid_text(self):
        r = requests.get(f"{BASE_URL}/api/trust-badge/rthr-deadbeefdeadbeef/badge.svg")
        assert r.status_code == 404
        assert "Invalid trust badge" in r.text
        assert "image/svg+xml" in r.headers.get("content-type", "")


# ============================= TRUST BADGE — HTML PAGE =============================

class TestVerifyPageHTML:
    def test_html_page_renders(self, fresh_user):
        badge_id = fresh_user["badge_id"]
        r = requests.get(f"{BASE_URL}/api/trust-badge/{badge_id}/page")
        assert r.status_code == 200, r.text
        assert "text/html" in r.headers.get("content-type", "")
        html = r.text
        assert "Compliance attestations" in html
        assert any(tier in html for tier in ("BRONZE", "SILVER", "GOLD"))
        # regulator text rendered
        assert "GDPR" in html and "HMRC" in html

    def test_html_invalid_404(self):
        r = requests.get(f"{BASE_URL}/api/trust-badge/rthr-deadbeefdeadbeef/page")
        assert r.status_code == 404
        assert "not valid" in r.text.lower()


# ============================= TIER ESCALATION via 2FA =============================

class TestTierEscalation:
    def test_enable_2fa_escalates_attestation(self, fresh_user):
        s = fresh_user["session"]
        # initial fetch
        r0 = s.get(f"{BASE_URL}/api/trust-badge/me")
        assert r0.status_code == 200
        before = r0.json()
        assert before["attestations"].get("owner_2fa_enabled") is False, \
            "expected new user not to have 2FA enabled"

        # Enable 2FA — endpoints in /api/2fa/setup/begin -> /api/2fa/setup/verify
        setup = s.post(f"{BASE_URL}/api/2fa/setup/begin")
        assert setup.status_code == 200, f"2FA setup/begin: {setup.status_code} {setup.text[:200]}"
        secret = setup.json().get("secret")
        assert secret, "2FA setup did not return a secret"
        try:
            import pyotp
        except ImportError:
            pytest.skip("pyotp not installed")
        code = pyotp.TOTP(secret).now()
        enable = s.post(f"{BASE_URL}/api/2fa/setup/verify", json={"code": code})
        assert enable.status_code == 200, f"enable 2FA failed: {enable.status_code} {enable.text[:200]}"

        # Re-fetch badge
        r1 = s.get(f"{BASE_URL}/api/trust-badge/me")
        assert r1.status_code == 200
        after = r1.json()
        assert after["attestations"].get("owner_2fa_enabled") is True, \
            f"2FA not reflected in attestations: {after['attestations']}"
        # tier may stay or move up — assert it didn't move DOWN
        tier_order = {"bronze": 1, "silver": 2, "gold": 3}
        assert tier_order[after["verified_level"]] >= tier_order[before["verified_level"]]


# ============================= DETERMINISM / SECURITY =============================

class TestBadgeDeterminism:
    def test_same_company_same_badge_id(self, fresh_user):
        s = fresh_user["session"]
        r1 = s.get(f"{BASE_URL}/api/trust-badge/me").json()
        r2 = s.get(f"{BASE_URL}/api/trust-badge/me").json()
        assert r1["badge_id"] == r2["badge_id"]

    def test_different_companies_different_badge_ids(self):
        ids = set()
        for _ in range(2):
            suffix = uuid.uuid4().hex[:8]
            s = requests.Session()
            s.headers.update({"Content-Type": "application/json"})
            r = s.post(f"{BASE_URL}/api/auth/register", json={
                "email": f"TEST_iter15_det_{suffix}@example.com",
                "password": "Test123!",
                "name": f"Det {suffix}",
                "company_name": f"TEST_Det_{suffix}",
            })
            assert r.status_code in (200, 201)
            s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
            d = s.get(f"{BASE_URL}/api/trust-badge/me").json()
            ids.add(d["badge_id"])
        assert len(ids) == 2, f"expected distinct badge_ids, got {ids}"

    def test_badge_id_format(self, fresh_user):
        bid = fresh_user["badge_id"]
        assert re.match(r"^rthr-[0-9a-f]{16}$", bid), f"bad format: {bid}"


# ============================= REGRESSION =============================

class TestRegression:
    def test_auth_me(self, fresh_user):
        r = fresh_user["session"].get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data.get("email") == fresh_user["email"]
        assert "company_id" in data

    def test_company_endpoint(self, fresh_user):
        r = fresh_user["session"].get(f"{BASE_URL}/api/company")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("name", "").startswith("TEST_Iter15Co_")

    def test_employees_endpoint(self, fresh_user):
        r = fresh_user["session"].get(f"{BASE_URL}/api/employees")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))
