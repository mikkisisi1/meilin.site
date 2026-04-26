"""
Iteration 18 regression tests.

Focus:
- This iteration only changed frontend i18n. Verify backend chat/tts/health
  still works and encryption pipeline (ENC1::) remains intact.
"""
import os
import re
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-psych-slim.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "miro_care")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def guest_token(session):
    r = session.post(f"{BASE_URL}/api/auth/guest", json={})
    assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in {data}"
    return token


@pytest.fixture(scope="module")
def auth_headers(guest_token):
    return {"Authorization": f"Bearer {guest_token}", "Content-Type": "application/json"}


# ---- Health ----
def test_health(session):
    r = session.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---- Core public GETs ----
@pytest.mark.parametrize("ep,wrapper", [
    ("/api/problems", "problems"),
    ("/api/tariffs", "tariffs"),
    ("/api/specialists", "specialists"),
])
def test_public_catalog(session, ep, wrapper):
    r = session.get(f"{BASE_URL}{ep}")
    assert r.status_code == 200
    data = r.json()
    assert wrapper in data, f"response missing wrapper '{wrapper}': {data}"
    assert data[wrapper]  # non-empty


# ---- Auth: admin login ----
def test_admin_login(session):
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@miro.care",
        "password": "MiroCare2026!",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("access_token") or data.get("token")


# ---- Chat + encryption at-rest ----
def test_chat_en_and_encryption(auth_headers):
    session_id = f"TEST_iter18_{uuid.uuid4().hex[:10]}"
    payload = {
        "session_id": session_id,
        "message": "Hello, I feel a little anxious today.",
        "voice": "female",
        "lang": "en",
        "length_mode": "short",
    }
    r = requests.post(f"{BASE_URL}/api/chat", json=payload, headers=auth_headers, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("response") or data.get("reply") or data.get("message"), f"No AI reply: {data}"
    reply = data.get("response") or data.get("reply") or data.get("message")
    assert len(reply) > 5

    # Check at-rest encryption: raw Mongo doc should have ENC1:: prefix
    mc = MongoClient(MONGO_URL)
    col = mc[DB_NAME]["chat_messages"]
    doc = col.find_one({"session_id": session_id})
    assert doc is not None, "No chat_messages doc persisted"
    raw_user = doc.get("user_message") or ""
    raw_ai = doc.get("ai_response") or ""
    assert raw_user.startswith("ENC1::"), f"user_message not encrypted at rest: {raw_user[:40]}"
    assert raw_ai.startswith("ENC1::"), f"ai_response not encrypted at rest: {raw_ai[:40]}"

    # History endpoint should decrypt and return plaintext
    h = requests.get(f"{BASE_URL}/api/chat/history/{session_id}", headers=auth_headers, timeout=30)
    assert h.status_code == 200, h.text
    hist = h.json()
    assert isinstance(hist, list) and len(hist) >= 1
    # no ENC1:: in returned payload
    serialized = str(hist)
    assert "ENC1::" not in serialized, "History leaked ENC1:: prefix"
    # The user message should be readable
    assert any("anxious" in (m.get("user_message") or "").lower() for m in hist)

    # Cleanup
    col.delete_many({"session_id": session_id})


# ---- TTS (Fish Audio) smoke ----
@pytest.mark.parametrize("voice,lang", [("male", "en"), ("female", "en")])
def test_tts(auth_headers, voice, lang):
    r = requests.post(
        f"{BASE_URL}/api/tts",
        json={"text": "Hello, this is a test.", "voice": voice, "lang": lang},
        headers=auth_headers,
        timeout=60,
    )
    assert r.status_code == 200, r.text
    ctype = r.headers.get("content-type", "")
    assert "audio" in ctype, f"unexpected content-type {ctype}"
    assert len(r.content) > 1024, "audio payload too small"
    # MP3 magic: 'ID3' or 0xFFFB/0xFFF3/0xFFF2
    head = r.content[:3]
    assert head == b"ID3" or r.content[0] == 0xFF, f"bad mp3 header: {head!r}"


# ---- i18n sanity: translations-extra has new keys in all 8 langs ----
def test_translations_extra_has_new_keys():
    path = "/app/frontend/src/contexts/translations-extra.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    required_keys = [
        "errorTryAgain", "bookingFailed", "paymentExpired", "paymentTimeout",
        "paymentError", "goToChat", "browserNoSpeech", "micDenied",
        "micUnavailable", "available", "booked", "yours", "perHour", "timeLabel",
    ]
    # Each key should appear at least 8 times (once per language)
    for k in required_keys:
        count = len(re.findall(rf"\b{k}\s*:", content))
        assert count >= 8, f"Key '{k}' appears only {count}x, expected >= 8 (one per lang)"
