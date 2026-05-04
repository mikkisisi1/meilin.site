"""
Iteration 9 — Post-refactoring regression tests for Miro.Care backend.
Verifies all endpoints work correctly after monolith → modules split.
Covers: auth, problems, tariffs, specialists, bookings, chat, user settings, payments.
"""
import pytest
import requests
import os
import uuid

BASE_URL: str = os.environ.get(
    'REACT_APP_BACKEND_URL',
    'https://slimlight-debug.preview.emergentagent.com'
).rstrip('/')

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@miro.care")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "MiroCare2026!")
TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "test@test.com")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "Test123!")


def get_auth_token(email: str, password: str) -> str:
    """Helper: login and return Bearer access token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"email": email, "password": password})
    if resp.status_code != 200:
        pytest.skip(f"Auth failed for {email}: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ────────────────────────────────────────────────────────────────
# 1. Backend startup sanity (public health check via problems)
# ────────────────────────────────────────────────────────────────
class TestBackendStartup:
    """Verifies backend is up and static routes respond after module split."""

    def test_problems_endpoint_responds(self):
        """GET /api/problems — 200 and correct shape (proves startup OK)"""
        resp = requests.get(f"{BASE_URL}/api/problems")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "problems" in data
        assert len(data["problems"]) == 10, f"Expected 10, got {len(data['problems'])}"

    def test_tariffs_endpoint_responds(self):
        """GET /api/tariffs — 200 and 4 tariffs"""
        resp = requests.get(f"{BASE_URL}/api/tariffs")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "tariffs" in data
        assert set(data["tariffs"].keys()) == {"test", "hour", "week", "month"}

    def test_specialists_endpoint_responds(self):
        """GET /api/specialists — 200 and at least 1 specialist"""
        resp = requests.get(f"{BASE_URL}/api/specialists")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "specialists" in data
        assert len(data["specialists"]) >= 1
        s = data["specialists"][0]
        assert s["id"] == "miron_shakira"
        assert "photo_url" in s


# ────────────────────────────────────────────────────────────────
# 2. Auth routes (routes/auth.py)
# ────────────────────────────────────────────────────────────────
class TestAuthRoutes:
    """POST /auth/guest, register, login, me, logout"""

    def test_create_guest_user(self):
        """POST /api/auth/guest — creates guest and returns token"""
        resp = requests.post(f"{BASE_URL}/api/auth/guest")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["role"] == "guest"
        assert data["user"].get("is_guest")
        assert "password_hash" not in data["user"]

    def test_register_new_user_returns_token(self):
        """POST /api/auth/register — new user, returns access_token and user"""
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@mirotest.com"
        resp = requests.post(f"{BASE_URL}/api/auth/register",
                             json={"email": email, "password": "TestPass123!", "name": "Iter9 User"})
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["user"]["email"] == email.lower()
        assert data["user"]["role"] == "user"
        assert "access_token" in data
        assert "password_hash" not in data["user"]

    def test_register_duplicate_returns_400(self):
        """POST /api/auth/register — duplicate email → 400"""
        email = f"TEST_dup_{uuid.uuid4().hex[:8]}@mirotest.com"
        requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": "TestPass123!"})
        resp = requests.post(f"{BASE_URL}/api/auth/register",
                             json={"email": email, "password": "OtherPass123!"})
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"

    def test_login_test_user_success(self):
        """POST /api/auth/login — test@test.com / Test123!"""
        resp = requests.post(f"{BASE_URL}/api/auth/login",
                             json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == TEST_USER_EMAIL

    def test_login_admin_success(self):
        """POST /api/auth/login — admin@miro.care / MiroCare2026!"""
        resp = requests.post(f"{BASE_URL}/api/auth/login",
                             json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["user"]["role"] == "admin"
        assert "access_token" in data

    def test_login_wrong_password_returns_401(self):
        """POST /api/auth/login — wrong password → 401"""
        resp = requests.post(f"{BASE_URL}/api/auth/login",
                             json={"email": ADMIN_EMAIL, "password": "WrongPass!"})
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_get_me_without_token_returns_401(self):
        """GET /api/auth/me — no token → 401"""
        resp = requests.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 401

    def test_get_me_with_admin_token(self):
        """GET /api/auth/me — valid admin token returns user object"""
        token = get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert "password_hash" not in data["user"]

    def test_get_me_with_test_user_token(self):
        """GET /api/auth/me — valid test user token"""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        assert resp.json()["user"]["email"] == TEST_USER_EMAIL

    def test_logout_clears_session(self):
        """POST /api/auth/logout — returns 200 with logged-out message"""
        resp = requests.post(f"{BASE_URL}/api/auth/logout")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "message" in data
        assert "Logged out" in data["message"] or "logged" in data["message"].lower()


# ────────────────────────────────────────────────────────────────
# 3. Lookup data (problems, tariffs, specialists)
# ────────────────────────────────────────────────────────────────
class TestLookupData:
    """Detailed validation of static data endpoints"""

    def test_problems_have_correct_structure(self):
        """GET /api/problems — all 10 categories with id, name, emoji, icon"""
        resp = requests.get(f"{BASE_URL}/api/problems")
        problems = resp.json()["problems"]
        assert len(problems) == 10
        expected_ids = ['anxiety', 'depression', 'relationships', 'ptsd', 'self_esteem',
                        'eating_disorder', 'weight', 'grief', 'meaning', 'other']
        actual_ids = [p["id"] for p in problems]
        for pid in expected_ids:
            assert pid in actual_ids, f"Missing problem ID: {pid}"
        for p in problems:
            assert "id" in p
            assert "name" in p
            assert "emoji" in p
            assert "icon" in p

    def test_tariffs_prices_and_minutes(self):
        """GET /api/tariffs — correct prices and minutes"""
        resp = requests.get(f"{BASE_URL}/api/tariffs")
        tariffs = resp.json()["tariffs"]
        assert tariffs["test"]["price"] == 0.0
        assert tariffs["test"]["minutes"] == 3
        assert tariffs["hour"]["price"] == 3.0
        assert tariffs["hour"]["minutes"] == 60
        assert tariffs["week"]["price"] == 14.0
        assert tariffs["week"]["minutes"] == 420
        assert tariffs["month"]["price"] == 29.0
        assert tariffs["month"]["minutes"] == 1800

    def test_specialists_filter_by_problem(self):
        """GET /api/specialists?problem=weight — returns at least 1 specialist"""
        resp = requests.get(f"{BASE_URL}/api/specialists?problem=weight")
        assert resp.status_code == 200
        data = resp.json()
        assert "specialists" in data
        assert len(data["specialists"]) >= 1


# ────────────────────────────────────────────────────────────────
# 4. Bookings routes (routes/bookings.py)
# ────────────────────────────────────────────────────────────────
class TestBookingsRoutes:
    """GET /bookings/slots, GET /bookings/my"""

    @pytest.fixture
    def token(self):
        return get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_get_booking_slots_requires_auth(self):
        """GET /api/bookings/slots — no auth → 401"""
        resp = requests.get(f"{BASE_URL}/api/bookings/slots")
        assert resp.status_code == 401

    def test_get_booking_slots_returns_calendar(self, token):
        """GET /api/bookings/slots — authenticated → calendar with weekday slots"""
        resp = requests.get(f"{BASE_URL}/api/bookings/slots",
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "calendar" in data
        assert "price" in data
        assert "advance_percent" in data

        # Should return ~21 working days (Mon-Fri only) out of 31 calendar days
        cal = data["calendar"]
        assert len(cal) >= 18, f"Expected >= 18 working days, got {len(cal)}"
        assert len(cal) <= 23, f"Expected <= 23 working days, got {len(cal)}"

        # Each day must have date, weekday, slots
        for day in cal[:3]:
            assert "date" in day
            assert "weekday" in day
            assert "slots" in day
            # No weekends (Mon=0..Fri=4)
            assert day["weekday"] in range(5), f"Weekend in calendar: {day}"
            # Each slot has time and status
            for slot in day["slots"]:
                assert "time" in slot
                assert "status" in slot
                assert slot["status"] in ("available", "booked", "own")

    def test_get_my_bookings_requires_auth(self):
        """GET /api/bookings/my — no auth → 401"""
        resp = requests.get(f"{BASE_URL}/api/bookings/my")
        assert resp.status_code == 401

    def test_get_my_bookings_returns_list(self, token):
        """GET /api/bookings/my — authenticated → list (may be empty)"""
        resp = requests.get(f"{BASE_URL}/api/bookings/my",
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "bookings" in data
        assert isinstance(data["bookings"], list)


# ────────────────────────────────────────────────────────────────
# 5. Chat routes (routes/chat.py)
# ────────────────────────────────────────────────────────────────
class TestChatRoutes:
    """GET /chat/history/{session_id}, GET /chat/sessions"""

    @pytest.fixture
    def token(self):
        return get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_chat_history_requires_auth(self):
        """GET /api/chat/history/xxx — no auth → 401"""
        resp = requests.get(f"{BASE_URL}/api/chat/history/test_session")
        assert resp.status_code == 401

    def test_chat_history_returns_messages(self, token):
        """GET /api/chat/history/{session_id} — authenticated → messages list"""
        session_id = f"iter9_test_{uuid.uuid4().hex[:8]}"
        resp = requests.get(f"{BASE_URL}/api/chat/history/{session_id}",
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_chat_sessions_requires_auth(self):
        """GET /api/chat/sessions — no auth → 401"""
        resp = requests.get(f"{BASE_URL}/api/chat/sessions")
        assert resp.status_code == 401

    def test_chat_sessions_returns_list(self, token):
        """GET /api/chat/sessions — authenticated → sessions list"""
        resp = requests.get(f"{BASE_URL}/api/chat/sessions",
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)


# ────────────────────────────────────────────────────────────────
# 6. User settings routes (routes/auth.py user section)
# ────────────────────────────────────────────────────────────────
class TestUserSettingsRoutes:
    """PUT /user/voice, PUT /user/language"""

    @pytest.fixture
    def token(self):
        return get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_update_voice_and_verify(self, token):
        """PUT /api/user/voice — updates voice preference, verify via GET /me"""
        resp = requests.put(f"{BASE_URL}/api/user/voice",
                            json={"voice": "female"},
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        assert "message" in resp.json()

        # Verify persistence
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert me.json()["user"]["selected_voice"] == "female"

    def test_update_language_and_verify(self, token):
        """PUT /api/user/language — updates language, verify via GET /me"""
        resp = requests.put(f"{BASE_URL}/api/user/language",
                            json={"language": "en"},
                            headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        assert "message" in resp.json()

        me = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert me.json()["user"]["selected_language"] == "en"

    def test_update_voice_requires_auth(self):
        """PUT /api/user/voice — no auth → 401"""
        resp = requests.put(f"{BASE_URL}/api/user/voice", json={"voice": "male"})
        assert resp.status_code == 401

    def test_update_language_requires_auth(self):
        """PUT /api/user/language — no auth → 401"""
        resp = requests.put(f"{BASE_URL}/api/user/language", json={"language": "ru"})
        assert resp.status_code == 401


# ────────────────────────────────────────────────────────────────
# 7. Payments routes (routes/payments.py)
# ────────────────────────────────────────────────────────────────
class TestPaymentsRoutes:
    """POST /payments/create-checkout"""

    @pytest.fixture
    def fresh_user_token(self):
        """Create a fresh user to test the test tariff (single use)."""
        email = f"TEST_pay_{uuid.uuid4().hex[:8]}@mirotest.com"
        resp = requests.post(f"{BASE_URL}/api/auth/register",
                             json={"email": email, "password": "TestPass123!"})
        if resp.status_code != 200:
            pytest.skip("Could not create fresh user for payment test")
        return resp.json()["access_token"]

    def test_create_checkout_test_tariff_activates(self, fresh_user_token):
        """POST /api/payments/create-checkout — test tariff → activated instantly"""
        resp = requests.post(f"{BASE_URL}/api/payments/create-checkout",
                             json={
                                 "tariff_id": "test",
                                 "origin_url": BASE_URL
                             },
                             headers=auth_headers(fresh_user_token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("type") == "test_activated", f"Expected test_activated, got {data}"

    def test_create_checkout_test_tariff_twice_fails(self, fresh_user_token):
        """POST /api/payments/create-checkout — test tariff second use → 400"""
        # First use
        requests.post(f"{BASE_URL}/api/payments/create-checkout",
                      json={"tariff_id": "test", "origin_url": BASE_URL},
                      headers=auth_headers(fresh_user_token))
        # Second use should fail
        resp = requests.post(f"{BASE_URL}/api/payments/create-checkout",
                             json={"tariff_id": "test", "origin_url": BASE_URL},
                             headers=auth_headers(fresh_user_token))
        assert resp.status_code == 400, f"Expected 400 on second test tariff, got {resp.status_code}"

    def test_create_checkout_invalid_tariff_returns_400(self, fresh_user_token):
        """POST /api/payments/create-checkout — invalid tariff_id → 400"""
        resp = requests.post(f"{BASE_URL}/api/payments/create-checkout",
                             json={"tariff_id": "nonexistent", "origin_url": BASE_URL},
                             headers=auth_headers(fresh_user_token))
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"

    def test_create_checkout_requires_auth(self):
        """POST /api/payments/create-checkout — no auth → 401"""
        resp = requests.post(f"{BASE_URL}/api/payments/create-checkout",
                             json={"tariff_id": "test", "origin_url": BASE_URL})
        assert resp.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
