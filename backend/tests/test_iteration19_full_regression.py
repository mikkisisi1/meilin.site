"""
Iteration 19 — full backend regression after OpenRouter key rotation + PWA addition.

Focus:
- /api/health
- /api/auth/guest + /api/auth/login (admin)
- /api/chat in RU + EN (AI reply not cut mid-word)
- At-rest encryption (chat_messages.user_message / ai_response → ENC1:: prefix)
- GET /api/chat/history/:id decrypts
- /api/tts male + female (valid MP3)
- Agent-switch across sessions (old session intact after new one created)
- /api/bookings/slots + /api/tariffs
- PUT /api/user/voice persists selected_voice
- PWA public assets (manifest.json, sw.js, icons)
"""
import os
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://slimlight-debug.preview.emergentagent.com",
).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "miro_care")

TIMEOUT_LONG = 90
TIMEOUT_SHORT = 30


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def guest_token(session):
    r = session.post(f"{BASE_URL}/api/auth/guest", json={}, timeout=TIMEOUT_SHORT)
    assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def admin_token(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@miro.care", "password": "MiroCare2026!"},
        timeout=TIMEOUT_SHORT,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def guest_headers(guest_token):
    return {"Authorization": f"Bearer {guest_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def mongo_col():
    mc = MongoClient(MONGO_URL)
    return mc[DB_NAME]["chat_messages"]


# ---------- health ----------
def test_health(session):
    r = session.get(f"{BASE_URL}/api/health", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------- auth ----------
def test_guest_auth_returns_jwt(guest_token):
    # JWT has 3 dot-separated segments
    assert guest_token.count(".") == 2


def test_admin_login_returns_jwt(admin_token):
    assert admin_token.count(".") == 2


def test_admin_me(admin_headers):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    data = r.json()
    user = data.get("user", data)
    assert user.get("email") == "admin@miro.care"


# ---------- chat RU + EN, not cut mid-word ----------
TERMINAL_PUNCT = set(".!?…。؟\"'»)")


def _ends_cleanly(text: str) -> bool:
    t = text.rstrip()
    if not t:
        return False
    return t[-1] in TERMINAL_PUNCT


@pytest.mark.parametrize("lang,message", [
    ("ru", "Привет! Расскажи подробно что такое когнитивно-поведенческая терапия и приведи 10 техник."),
    ("en", "Hello, can you describe in detail what cognitive-behavioural therapy is and list 10 techniques?"),
])
def test_chat_long_reply_ends_on_sentence(guest_headers, mongo_col, lang, message):
    sid = f"TEST_iter19_chat_{lang}_{uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "session_id": sid,
            "message": message,
            "voice": "male",
            "lang": lang,
            "length_mode": "long",
        },
        headers=guest_headers,
        timeout=TIMEOUT_LONG,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    reply = data.get("message") or data.get("response") or data.get("reply") or ""
    assert len(reply) > 20, f"reply too short: {reply!r}"
    # Remove trailing whitespace + common closing chars; final char must be sentence terminator
    assert _ends_cleanly(reply), f"Reply cut mid-word (lang={lang}): tail={reply[-60:]!r}"
    # Cleanup
    mongo_col.delete_many({"session_id": sid})


# ---------- encryption at rest ----------
def test_encryption_at_rest(guest_headers, mongo_col):
    sid = f"TEST_iter19_enc_{uuid.uuid4().hex[:8]}"
    user_msg = "I feel anxious and sad today."
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"session_id": sid, "message": user_msg, "voice": "female", "lang": "en", "length_mode": "short"},
        headers=guest_headers,
        timeout=TIMEOUT_LONG,
    )
    assert r.status_code == 200, r.text

    doc = mongo_col.find_one({"session_id": sid})
    assert doc is not None, "chat_messages row not persisted"
    raw_user = doc.get("user_message") or ""
    raw_ai = doc.get("ai_response") or ""
    assert raw_user.startswith("ENC1::"), f"user_message not encrypted: {raw_user[:50]!r}"
    assert raw_ai.startswith("ENC1::"), f"ai_response not encrypted: {raw_ai[:50]!r}"

    # History endpoint decrypts
    h = requests.get(
        f"{BASE_URL}/api/chat/history/{sid}",
        headers=guest_headers,
        timeout=TIMEOUT_SHORT,
    )
    assert h.status_code == 200, h.text
    hist = h.json()
    serialized = str(hist)
    assert "ENC1::" not in serialized, "History leaked ENC1:: prefix"
    assert "anxious" in serialized.lower()

    mongo_col.delete_many({"session_id": sid})


# ---------- TTS ----------
@pytest.mark.parametrize("voice", ["male", "female"])
def test_tts_mp3(guest_headers, voice):
    r = requests.post(
        f"{BASE_URL}/api/tts",
        json={"text": "Привет, это проверка.", "voice": voice, "lang": "ru"},
        headers=guest_headers,
        timeout=TIMEOUT_LONG,
    )
    assert r.status_code == 200, r.text
    ctype = r.headers.get("content-type", "")
    assert "audio" in ctype.lower(), f"bad content-type: {ctype}"
    assert len(r.content) > 1024, "mp3 too small"
    head = r.content[:3]
    assert head == b"ID3" or r.content[0] == 0xFF, f"bad mp3 magic: {head!r}"


# ---------- agent switch: two sessions coexist ----------
def test_agent_switch_sessions_coexist(guest_headers, mongo_col):
    sid_a = f"TEST_iter19_A_{uuid.uuid4().hex[:8]}"
    sid_b = f"TEST_iter19_B_{uuid.uuid4().hex[:8]}"

    r1 = requests.post(
        f"{BASE_URL}/api/chat",
        json={"session_id": sid_a, "message": "Hello Miron", "voice": "male", "lang": "en", "length_mode": "short"},
        headers=guest_headers, timeout=TIMEOUT_LONG,
    )
    assert r1.status_code == 200, r1.text

    r2 = requests.post(
        f"{BASE_URL}/api/chat",
        json={"session_id": sid_b, "message": "Hello Oksana", "voice": "female", "lang": "en", "length_mode": "short"},
        headers=guest_headers, timeout=TIMEOUT_LONG,
    )
    assert r2.status_code == 200, r2.text

    # Both sessions should have rows
    a_docs = list(mongo_col.find({"session_id": sid_a}))
    b_docs = list(mongo_col.find({"session_id": sid_b}))
    assert len(a_docs) >= 1, "session A has no rows"
    assert len(b_docs) >= 1, "session B has no rows"

    # History of A unaffected by B
    ha = requests.get(f"{BASE_URL}/api/chat/history/{sid_a}", headers=guest_headers, timeout=TIMEOUT_SHORT)
    assert ha.status_code == 200
    ha_data = ha.json()
    assert "Oksana" not in str(ha_data), "session A leaked session B content"

    mongo_col.delete_many({"session_id": {"$in": [sid_a, sid_b]}})


# ---------- bookings + tariffs ----------
def test_bookings_slots(session):
    r = session.get(f"{BASE_URL}/api/bookings/slots", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200, r.text
    data = r.json()
    # Flexible: accept list or dict wrapper
    if isinstance(data, dict):
        assert any(k in data for k in ("slots", "days", "calendar", "items"))
    else:
        assert isinstance(data, list)


def test_tariffs(session):
    r = session.get(f"{BASE_URL}/api/tariffs", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    data = r.json()
    assert "tariffs" in data
    tariffs = data["tariffs"]
    # Accept list or dict-map
    assert tariffs and (isinstance(tariffs, list) or isinstance(tariffs, dict))
    if isinstance(tariffs, dict):
        assert len(tariffs) >= 1
        first = next(iter(tariffs.values()))
        assert "price" in first and "name" in first


# ---------- PUT /api/user/voice ----------
def test_put_user_voice_persists(guest_headers):
    # Use a fresh requests session to avoid cookie leakage between fixtures
    s = requests.Session()
    r = s.put(
        f"{BASE_URL}/api/user/voice",
        json={"voice": "female"},
        headers=guest_headers,
        timeout=TIMEOUT_SHORT,
    )
    assert r.status_code == 200, r.text
    me = s.get(f"{BASE_URL}/api/auth/me", headers=guest_headers, timeout=TIMEOUT_SHORT)
    assert me.status_code == 200
    u = me.json().get("user", me.json())
    assert u.get("selected_voice") == "female"

    r2 = s.put(
        f"{BASE_URL}/api/user/voice",
        json={"voice": "male"},
        headers=guest_headers,
        timeout=TIMEOUT_SHORT,
    )
    assert r2.status_code == 200
    me2 = s.get(f"{BASE_URL}/api/auth/me", headers=guest_headers, timeout=TIMEOUT_SHORT)
    u2 = me2.json().get("user", me2.json())
    assert u2.get("selected_voice") == "male"


# ---------- PWA assets ----------
def test_pwa_manifest_served():
    r = requests.get(f"{BASE_URL}/manifest.json", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    assert "json" in r.headers.get("content-type", "").lower()
    data = r.json()
    assert data.get("name") or data.get("short_name")
    # icons present
    icons = data.get("icons") or []
    assert len(icons) >= 1


def test_pwa_service_worker_served():
    r = requests.get(f"{BASE_URL}/sw.js", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "").lower()
    assert "javascript" in ctype
    assert len(r.text) > 100


@pytest.mark.parametrize("path", ["/icon-192.png", "/icon-512.png"])
def test_pwa_icons_served(path):
    r = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT_SHORT)
    assert r.status_code == 200
    assert "image/png" in r.headers.get("content-type", "").lower()
    assert len(r.content) > 200
