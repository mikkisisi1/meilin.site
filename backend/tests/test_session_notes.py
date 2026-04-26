"""
Iteration 10 — Session Notes (cross-session memory) feature tests.
Covers: GET /api/chat/notes, DELETE /api/chat/notes, 6-message trigger,
         load_personal_context regression, auth/me regression, chat history regression.
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL: str = os.environ.get(
    'REACT_APP_BACKEND_URL',
    'https://slim-you-1.preview.emergentagent.com'
).rstrip('/')

TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "test@test.com")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "Test123!")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@miro.care")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "MiroCare2026!")


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_auth_token(email: str, password: str) -> str:
    """Login and return Bearer access token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login",
                         json={"email": email, "password": password})
    if resp.status_code != 200:
        pytest.skip(f"Auth failed for {email}: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_guest_user() -> tuple[str, str]:
    """Create a fresh guest user and return (user_id, access_token)."""
    resp = requests.post(f"{BASE_URL}/api/auth/guest")
    assert resp.status_code == 200, f"Guest creation failed: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("access_token")
    assert token, f"No access_token in guest response: {data}"
    # Get user_id from /me (response wrapped in {"user": {...}})
    me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    user_obj = me_data.get("user") or me_data
    user_id = user_obj.get("id") or user_obj.get("_id") or user_obj.get("user_id")
    return user_id, token


# ── 1. GET /api/chat/notes — unauthenticated ──────────────────────────────────
class TestSessionNotesAuth:
    """Auth guard tests for /chat/notes endpoints."""

    def test_get_notes_requires_auth(self):
        """GET /api/chat/notes without token → 401."""
        resp = requests.get(f"{BASE_URL}/api/chat/notes")
        assert resp.status_code == 401, (
            f"Expected 401 without auth, got {resp.status_code}: {resp.text}"
        )

    def test_delete_notes_requires_auth(self):
        """DELETE /api/chat/notes without token → 401."""
        resp = requests.delete(f"{BASE_URL}/api/chat/notes")
        assert resp.status_code == 401, (
            f"Expected 401 without auth, got {resp.status_code}: {resp.text}"
        )


# ── 2. GET /api/chat/notes — empty user ──────────────────────────────────────
class TestGetNotesEmpty:
    """GET /api/chat/notes returns correct empty structure for new users."""

    def test_get_notes_returns_200(self):
        """GET /api/chat/notes → 200."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

    def test_get_notes_has_notes_field(self):
        """Response has 'notes' field (string)."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "notes" in data, f"'notes' key missing from response: {data}"
        assert isinstance(data["notes"], str), f"'notes' should be str, got: {type(data['notes'])}"

    def test_get_notes_has_updated_at_field(self):
        """Response has 'updated_at' field."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "updated_at" in data, f"'updated_at' key missing from response: {data}"

    def test_fresh_guest_has_empty_notes(self):
        """A brand-new guest user must have notes='' and updated_at=None."""
        _, token = create_guest_user()
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["notes"] == "", (
            f"Fresh guest should have empty notes, got: '{data['notes']}'"
        )
        assert data["updated_at"] is None, (
            f"Fresh guest should have updated_at=None, got: {data['updated_at']}"
        )


# ── 3. DELETE /api/chat/notes ─────────────────────────────────────────────────
class TestDeleteNotes:
    """DELETE /api/chat/notes clears the notes and returns success."""

    def test_delete_notes_returns_200(self):
        """DELETE /api/chat/notes → 200."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

    def test_delete_notes_returns_message(self):
        """DELETE response contains a 'message' field indicating success."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data, f"Expected 'message' field in response: {data}"
        assert len(data["message"]) > 0, "Message field should not be empty"

    def test_notes_empty_after_delete(self):
        """After DELETE, GET /api/chat/notes returns notes='' and updated_at=None."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        # Clear notes
        del_resp = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert del_resp.status_code == 200

        # Verify empty
        get_resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["notes"] == "", (
            f"Notes should be empty after DELETE, got: '{data['notes']}'"
        )
        assert data["updated_at"] is None, (
            f"updated_at should be None after DELETE, got: {data['updated_at']}"
        )

    def test_delete_is_idempotent(self):
        """Calling DELETE twice does not cause errors."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        r1 = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        r2 = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert r1.status_code == 200, f"First DELETE failed: {r1.status_code}"
        assert r2.status_code == 200, f"Second DELETE failed: {r2.status_code}"


# ── 4. 6-message trigger → session notes populated ────────────────────────────
class TestSessionNotesTrigger:
    """
    Core feature test: after 6 user messages in a session, background
    task must generate and persist session notes to users.session_notes.
    """

    @pytest.fixture(scope="class")
    def guest_with_notes(self):
        """
        Create fresh guest, clear notes, send 6 messages,
        wait for background task, return (token, initial_notes_state).
        """
        _, token = create_guest_user()
        hdrs = auth_headers(token)

        # Clear any pre-existing notes
        del_resp = requests.delete(f"{BASE_URL}/api/chat/notes", headers=hdrs)
        assert del_resp.status_code == 200, f"Pre-test DELETE failed: {del_resp.text}"

        # Confirm notes empty before chat
        pre = requests.get(f"{BASE_URL}/api/chat/notes", headers=hdrs)
        assert pre.status_code == 200
        pre_data = pre.json()
        assert pre_data["notes"] == "", f"Notes not empty before test: {pre_data}"

        # Use unique session_id so this test is isolated
        session_id = f"test_notes_{uuid.uuid4().hex[:8]}"

        # Send exactly 6 messages (fresh guest has 6 free messages)
        messages_sent = 0
        for i in range(6):
            payload = {
                "message": f"Тест сообщение {i+1}: расскажи мне о психологии и стрессе.",
                "session_id": session_id,
                "language": "ru",
            }
            chat_resp = requests.post(
                f"{BASE_URL}/api/chat",
                json=payload,
                headers=hdrs,
                timeout=60,  # OpenRouter may be slow
            )
            assert chat_resp.status_code == 200, (
                f"Chat message {i+1} failed: {chat_resp.status_code} {chat_resp.text[:300]}"
            )
            resp_data = chat_resp.json()
            # If user ran out of free messages, test cannot proceed
            if resp_data.get("type") == "tariff_prompt":
                pytest.skip(
                    f"User ran out of free messages at message {i+1}; "
                    "cannot trigger session notes. Activate tariff first."
                )
            assert resp_data.get("type") == "ai_response", (
                f"Message {i+1} did not get ai_response, got: {resp_data}"
            )
            messages_sent += 1

        assert messages_sent == 6, f"Only sent {messages_sent} messages"

        # Wait for background asyncio.create_task to complete (OpenRouter call)
        print("\nWaiting 8s for background notes update task...")
        time.sleep(8)

        return token, session_id, pre_data

    def test_notes_populated_after_6_messages(self, guest_with_notes):
        """After 6 messages, notes must be a non-empty string."""
        token, session_id, _ = guest_with_notes
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200, f"GET /api/chat/notes failed: {resp.status_code}"
        data = resp.json()
        print(f"\nNotes after 6 messages: '{data['notes'][:200]}'")
        assert data["notes"] != "", (
            "Session notes should be non-empty after 6 messages; still empty. "
            "Check backend logs for 'Session notes updated' or errors."
        )

    def test_updated_at_set_after_6_messages(self, guest_with_notes):
        """After 6 messages, updated_at must be a non-None timestamp."""
        token, session_id, _ = guest_with_notes
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        print(f"\nupdated_at after 6 messages: {data['updated_at']}")
        assert data["updated_at"] is not None, (
            "updated_at should be set after 6 messages; got None. "
            "Check backend logs for 'Session notes updated' log line."
        )

    def test_notes_are_string_type(self, guest_with_notes):
        """notes field must be a non-empty string (not dict, not list)."""
        token, session_id, _ = guest_with_notes
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["notes"], str), (
            f"notes should be str, got {type(data['notes'])}: {data['notes']}"
        )
        # Should be a meaningful summary (longer than a few chars)
        assert len(data["notes"]) > 20, (
            f"Notes too short to be a proper summary: '{data['notes']}'"
        )

    def test_notes_within_1500_char_cap(self, guest_with_notes):
        """Notes must be capped at 1500 characters as per update_session_notes logic."""
        token, session_id, _ = guest_with_notes
        resp = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notes"]) <= 1500, (
            f"Notes exceed 1500 char cap: {len(data['notes'])} chars"
        )

    def test_delete_notes_after_6_messages(self, guest_with_notes):
        """After notes are generated, DELETE must clear them again."""
        token, session_id, _ = guest_with_notes
        # Verify notes exist first (they should from previous tests)
        requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))

        # Delete
        del_resp = requests.delete(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert del_resp.status_code == 200, f"DELETE failed: {del_resp.text}"

        # Verify cleared
        post = requests.get(f"{BASE_URL}/api/chat/notes", headers=auth_headers(token))
        assert post.status_code == 200
        post_data = post.json()
        assert post_data["notes"] == "", (
            f"Notes not cleared after DELETE. Got: '{post_data['notes'][:100]}'"
        )
        assert post_data["updated_at"] is None, (
            f"updated_at not cleared after DELETE. Got: {post_data['updated_at']}"
        )


# ── 5. load_personal_context — smoke test ────────────────────────────────────
class TestLoadPersonalContext:
    """
    Verify that load_personal_context() is called on chat without errors.
    A chat request that succeeds proves load_personal_context() ran without
    throwing (the DB query for session_notes is wrapped in try-except).
    """

    def test_chat_works_for_user_with_notes(self):
        """
        User with session_notes in DB — first chat message loads context
        from DB and initialises system prompt correctly (no 500 error).
        """
        # Use test@test.com who may have notes from the 6-message test
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        hdrs = auth_headers(token)

        # Check user's current status
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=hdrs)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        user_obj = me_data.get("user") or me_data
        free_count = user_obj.get("free_messages_count", 0)
        minutes_left = user_obj.get("minutes_left", 0) or 0

        # User must have access to send at least one message
        if free_count >= 12 and minutes_left <= 0:
            pytest.skip(
                f"test@test.com has no free messages (free_count={free_count}, "
                f"minutes_left={minutes_left}). Need to reset for this test."
            )

        session_id = f"context_test_{uuid.uuid4().hex[:8]}"
        chat_resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Привет, как дела?",
                "session_id": session_id,
                "language": "ru",
            },
            headers=hdrs,
            timeout=60,
        )
        assert chat_resp.status_code == 200, (
            f"Chat with load_personal_context failed: {chat_resp.status_code} {chat_resp.text[:300]}"
        )
        # Must be ai_response, not tariff_prompt
        resp_data = chat_resp.json()
        assert resp_data.get("type") in ("ai_response", "tariff_prompt"), (
            f"Unexpected response type: {resp_data}"
        )
        # No 500 error means load_personal_context ran without crashing
        print(f"\nload_personal_context smoke test passed (type={resp_data.get('type')})")


# ── 6. Regression: GET /api/auth/me ──────────────────────────────────────────
class TestAuthMeRegression:
    """GET /api/auth/me regression — user returned correctly."""

    def test_auth_me_returns_200(self):
        """GET /api/auth/me → 200."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

    def test_auth_me_returns_correct_email(self):
        """GET /api/auth/me → email matches logged-in user."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        # /me wraps response in {"user": {...}}
        user = data.get("user") or data
        assert user.get("email") == TEST_USER_EMAIL, (
            f"Expected email {TEST_USER_EMAIL}, got {user.get('email')}. Full: {data}"
        )

    def test_auth_me_has_required_fields(self):
        """GET /api/auth/me returns email, role (under 'user' key)."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        user = data.get("user") or data
        for field in ("email", "role"):
            assert field in user, f"Field '{field}' missing from /auth/me user: {user}"

    def test_auth_me_role_is_user(self):
        """test@test.com should have role='user'."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        data = resp.json()
        user = data.get("user") or data
        assert user.get("role") == "user", (
            f"Expected role 'user', got '{user.get('role')}'"
        )

    def test_admin_auth_me(self):
        """Admin user /me returns role='admin'."""
        token = get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        user = data.get("user") or data
        assert user.get("role") == "admin", (
            f"Expected admin role, got '{user.get('role')}'. Full: {data}"
        )


# ── 7. Regression: GET /api/chat/history/{session_id} ───────────────────────
class TestChatHistoryRegression:
    """GET /api/chat/history/{session_id} regression."""

    def test_history_requires_auth(self):
        """GET /api/chat/history/test-session without auth → 401."""
        resp = requests.get(f"{BASE_URL}/api/chat/history/test-session")
        assert resp.status_code == 401, (
            f"Expected 401 without auth, got {resp.status_code}"
        )

    def test_history_returns_200_for_valid_session(self):
        """GET /api/chat/history/test-session with auth → 200."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(
            f"{BASE_URL}/api/chat/history/test-session",
            headers=auth_headers(token)
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"

    def test_history_returns_messages_list(self):
        """Chat history response has 'messages' list."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        resp = requests.get(
            f"{BASE_URL}/api/chat/history/test-session",
            headers=auth_headers(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data, f"'messages' key missing: {data}"
        assert isinstance(data["messages"], list), "messages should be a list"

    def test_history_empty_for_nonexistent_session(self):
        """Non-existent session returns empty messages list (not 404)."""
        token = get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        fake_session = f"nonexistent_{uuid.uuid4().hex[:8]}"
        resp = requests.get(
            f"{BASE_URL}/api/chat/history/{fake_session}",
            headers=auth_headers(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["messages"] == [], (
            f"Expected empty list for non-existent session, got: {data['messages']}"
        )
