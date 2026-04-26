"""Iteration 23: B1-B5 backend tests for new endpoints.
Covers:
- DELETE /api/chat/messages (auth required, clears only chat_messages, keeps users/intake)
- POST /api/specialist/request (auth required, requires only `contact`, persists with status='new')
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://slim-you-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "miro_care")


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module")
def guest_token():
    """Create a guest user via POST /api/auth/guest and return the access_token."""
    r = requests.post(f"{API}/auth/guest", timeout=15)
    assert r.status_code == 200, f"guest login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token")
    assert token, f"no access_token: {data}"
    return token


@pytest.fixture(scope="module")
def auth_headers(guest_token):
    return {"Authorization": f"Bearer {guest_token}", "Content-Type": "application/json"}


# ---------- Auth required (401 without token) ----------

class TestAuthRequired:
    def test_clear_messages_requires_auth(self):
        r = requests.delete(f"{API}/chat/messages", timeout=10)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_specialist_request_requires_auth(self):
        r = requests.post(f"{API}/specialist/request",
                          json={"contact": "+79991112233"}, timeout=10)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


# ---------- DELETE /api/chat/messages ----------

class TestClearChatMessages:
    def test_clear_returns_proper_shape(self, auth_headers):
        r = requests.delete(f"{API}/chat/messages", headers=auth_headers, timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "message" in data
        assert "deleted" in data
        assert isinstance(data["deleted"], int)

    def test_clear_does_not_touch_user_profile_or_intake(self, guest_token, auth_headers, mongo_db):
        # Decode user id from token
        import jwt as pyjwt
        payload = pyjwt.decode(guest_token, options={"verify_signature": False})
        uid = payload["sub"]

        # Confirm user exists before
        user_before = mongo_db.users.find_one({"_id": ObjectId(uid)})
        assert user_before is not None, "guest user not found in users collection"

        # Seed a chat_messages doc + an intake-like field on the user
        mongo_db.chat_messages.insert_one({
            "user_id": uid,
            "session_id": "TEST_iter23_session",
            "role": "user",
            "content": "TEST_iter23 message",
            "created_at": time.time(),
        })
        mongo_db.users.update_one(
            {"_id": ObjectId(uid)},
            {"$set": {"intake": {"name": "TEST_iter23", "step": -2}, "language": "ru"}}
        )

        # Sanity: at least 1 message exists
        msgs_before = mongo_db.chat_messages.count_documents({"user_id": uid})
        assert msgs_before >= 1

        # Call the delete endpoint
        r = requests.delete(f"{API}/chat/messages", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["deleted"] >= 1

        # Verify chat_messages for this user are gone
        msgs_after = mongo_db.chat_messages.count_documents({"user_id": uid})
        assert msgs_after == 0, f"messages remained: {msgs_after}"

        # Verify the user document still exists with intake/language preserved
        user_after = mongo_db.users.find_one({"_id": ObjectId(uid)})
        assert user_after is not None, "user was deleted by clear chat — BUG"
        assert user_after.get("intake", {}).get("name") == "TEST_iter23", \
            "intake.name was wiped by clear chat — BUG"
        assert user_after.get("intake", {}).get("step") == -2, \
            "intake.step was wiped by clear chat — BUG"
        assert user_after.get("language") == "ru", \
            "language was wiped by clear chat — BUG"


# ---------- POST /api/specialist/request ----------

class TestSpecialistRequest:
    def test_minimal_payload_only_contact(self, auth_headers, guest_token, mongo_db):
        payload = {"contact": "TEST_iter23+79990001122"}
        r = requests.post(f"{API}/specialist/request", json=payload,
                          headers=auth_headers, timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "message" in data

        # Verify persisted
        import jwt as pyjwt
        uid = pyjwt.decode(guest_token, options={"verify_signature": False})["sub"]
        doc = mongo_db.specialist_requests.find_one(
            {"user_id": uid, "contact": "TEST_iter23+79990001122"}
        )
        assert doc is not None, "request not persisted"
        assert doc["status"] == "new"
        assert doc["channel"] == "form"  # default
        assert doc.get("name") is None
        assert doc.get("note") is None

    def test_full_payload(self, auth_headers, guest_token, mongo_db):
        payload = {
            "name": "TEST_iter23 Ivan",
            "contact": "TEST_iter23+79995554433",
            "note": "Need urgent consultation",
            "channel": "whatsapp",
        }
        r = requests.post(f"{API}/specialist/request", json=payload,
                          headers=auth_headers, timeout=15)
        assert r.status_code == 200
        import jwt as pyjwt
        uid = pyjwt.decode(guest_token, options={"verify_signature": False})["sub"]
        doc = mongo_db.specialist_requests.find_one(
            {"user_id": uid, "contact": "TEST_iter23+79995554433"}
        )
        assert doc is not None
        assert doc["name"] == "TEST_iter23 Ivan"
        assert doc["note"] == "Need urgent consultation"
        assert doc["channel"] == "whatsapp"
        assert doc["status"] == "new"
        assert "created_at" in doc

    def test_missing_contact_returns_422(self, auth_headers):
        r = requests.post(f"{API}/specialist/request",
                          json={"note": "no contact"}, headers=auth_headers, timeout=10)
        assert r.status_code in (400, 422), f"{r.status_code} {r.text}"

    @classmethod
    def teardown_class(cls):
        # Cleanup TEST_ specialist_requests
        client = MongoClient(MONGO_URL)
        try:
            client[DB_NAME].specialist_requests.delete_many(
                {"contact": {"$regex": "^TEST_iter23"}}
            )
        finally:
            client.close()
