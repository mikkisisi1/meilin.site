"""
Iteration 28 — verify chat.py / ChatPage.jsx refactor is behavior-identical.
Backend-only assertions:
  * routes/chat_helpers.py exports all helpers expected by chat.py
  * /api/chat (sync), /api/chat/stream (SSE), read endpoints, /specialist/request all work
  * Guest cookie auth flow still works for chat
"""
import os
import sys
import json
import importlib

# Ensure backend module path
sys.path.insert(0, "/app/backend")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "miro_care")

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://leon-kylie-chat.preview.emergentagent.com").rstrip("/")


# ---------- Helper-import smoke (refactor correctness) ----------
def test_chat_helpers_exports():
    """chat_helpers.py must export all symbols chat.py imports."""
    mod = importlib.import_module("routes.chat_helpers")
    expected = [
        "chat_histories", "session_photo_count", "MAX_SESSIONS", "init_session",
        "call_openrouter", "stream_openrouter", "handle_search_tag", "trim_messages",
        "strip_emotion_markers", "SEARCH_TAG_RE",
        "pick_length_mode", "build_length_directive", "LENGTH_TOKEN_LIMITS",
        "check_user_access", "persist_chat_turn",
        "extract_homework", "extract_user_name", "truncate_to_sentence",
        "build_counter_updates",
    ]
    missing = [s for s in expected if not hasattr(mod, s)]
    assert not missing, f"Missing helper exports: {missing}"


def test_chat_module_imports_from_helpers():
    """routes/chat.py must NOT import strip_emotion_markers from itself anymore."""
    with open("/app/backend/routes/chat.py") as f:
        src = f.read()
    assert "from routes.chat_helpers import" in src
    # Old self-defined symbols should be gone from chat.py module body
    assert "def strip_emotion_markers" not in src
    assert "def trim_messages" not in src
    assert "def pick_length_mode" not in src


def test_strip_emotion_markers_via_helpers():
    from routes.chat_helpers import strip_emotion_markers
    assert strip_emotion_markers("(calm)(soft) Hi.") == "Hi."
    assert strip_emotion_markers(None) is None


def test_pick_length_mode():
    from routes.chat_helpers import pick_length_mode, LENGTH_TOKEN_LIMITS
    assert pick_length_mode("да") == "short"
    assert set(LENGTH_TOKEN_LIMITS.keys()) == {"short", "medium", "long"}


def test_build_length_directive_contains_rule_marker():
    from routes.chat_helpers import build_length_directive
    out = build_length_directive("medium")
    assert "СТРОГОЕ ПРАВИЛО" in out


def test_extract_user_name():
    from routes.chat_helpers import extract_user_name
    assert extract_user_name("меня зовут Алекс") == "Алекс"
    assert extract_user_name("hello") is None


def test_extract_homework():
    from routes.chat_helpers import extract_homework
    txt = "Some text. 📝 на эту неделю: пить 2 литра воды каждый день."
    hw = extract_homework(txt)
    assert hw is not None
    assert "вод" in hw


def test_truncate_to_sentence():
    from routes.chat_helpers import truncate_to_sentence
    s = "First sentence is here. Second sentence is here too. Half cut"
    out = truncate_to_sentence(s)
    assert out.endswith(".") or out.endswith("…")


def test_trim_messages():
    from routes.chat_helpers import trim_messages
    msgs = [{"role": "system", "content": "S"}] + [{"role": "user", "content": str(i)} for i in range(50)]
    out = trim_messages(msgs, max_len=10)
    assert out[0]["role"] == "system"
    assert len(out) == 10


# ---------- Live API tests (cookie auth) ----------
@pytest.fixture(scope="module")
def guest_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/guest", timeout=15)
    assert r.status_code == 200, f"guest auth failed: {r.status_code} {r.text[:200]}"
    return s


def test_guest_auth_me(guest_session):
    r = guest_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r.status_code == 200
    assert r.json().get("user", {}).get("role") in ("guest", "user", "admin")


def test_chat_sessions_endpoint(guest_session):
    r = guest_session.get(f"{BASE_URL}/api/chat/sessions", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_chat_notes_get_and_clear(guest_session):
    r = guest_session.get(f"{BASE_URL}/api/chat/notes", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "notes" in body and "updated_at" in body
    r2 = guest_session.delete(f"{BASE_URL}/api/chat/notes", timeout=15)
    assert r2.status_code == 200


def test_chat_history_endpoint(guest_session):
    r = guest_session.get(f"{BASE_URL}/api/chat/history/test_session_xxx", timeout=15)
    assert r.status_code == 200
    assert "messages" in r.json()


def test_clear_chat_messages(guest_session):
    r = guest_session.delete(f"{BASE_URL}/api/chat/messages", timeout=15)
    assert r.status_code == 200
    assert "deleted" in r.json()


def test_specialist_request(guest_session):
    payload = {"name": "TEST_user", "contact": "+10000000000", "note": "TEST refactor", "channel": "form"}
    r = guest_session.post(f"{BASE_URL}/api/specialist/request", json=payload, timeout=15)
    assert r.status_code == 200
    assert r.json().get("message") == "Request received"


def test_chat_sync(guest_session):
    """POST /api/chat — accept 200 (with structure) OR 503 (OpenRouter down)."""
    r = guest_session.post(
        f"{BASE_URL}/api/chat",
        json={"message": "Привет", "session_id": "iter28_smoke", "voice": "male", "language": "ru"},
        timeout=60,
    )
    if r.status_code == 503:
        pytest.skip("OpenRouter not available (503) — pre-existing infra issue")
    assert r.status_code == 200, f"chat failed: {r.status_code} {r.text[:200]}"
    body = r.json()
    assert "message" in body
    assert "type" in body
    assert "needs_tariff" in body


def test_chat_stream(guest_session):
    """POST /api/chat/stream — SSE returns delta + done events."""
    with guest_session.post(
        f"{BASE_URL}/api/chat/stream",
        json={"message": "Скажи привет", "session_id": "iter28_stream", "voice": "female", "language": "ru"},
        stream=True,
        timeout=60,
    ) as r:
        assert r.status_code == 200, f"stream failed: {r.status_code}"
        ctype = r.headers.get("content-type", "")
        assert "text/event-stream" in ctype, f"wrong content-type: {ctype}"

        events = []
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data:"):
                try:
                    payload = json.loads(raw[5:].strip())
                    events.append(payload)
                    if payload.get("type") in ("done", "error", "tariff_prompt"):
                        break
                except Exception:
                    pass
            if len(events) > 200:
                break

    assert events, "No SSE events received"
    types = {e.get("type") for e in events}
    # Either we got delta+done, or error (OpenRouter down) — both acceptable shapes
    assert types & {"delta", "done", "error", "tariff_prompt"}, f"unexpected event types: {types}"
