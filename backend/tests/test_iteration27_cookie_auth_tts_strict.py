"""
Iteration 27 backend tests:
  - JWT migration to httpOnly cookies (auth/guest, login, register, logout, me)
  - TTS strict-voice mode (only 'male' or 'female' accepted)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://slimlight-debug.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@miro.care"
ADMIN_PASSWORD = "MiroCare2026!"


# ---------- helpers ----------
def _has_cookie_set(resp, name):
    """Inspect Set-Cookie headers to confirm cookie is being set with HttpOnly."""
    cookies = resp.headers.get_all("Set-Cookie") if hasattr(resp.headers, "get_all") else None
    if cookies is None:
        # requests stores raw headers via raw.headers (multi)
        try:
            cookies = resp.raw.headers.get_all("Set-Cookie")
        except Exception:
            cookies = [h for k, h in resp.raw.headers.items() if k.lower() == "set-cookie"] if resp.raw else []
    if not cookies:
        # fall back: single combined header
        single = resp.headers.get("Set-Cookie", "")
        cookies = [single] if single else []
    for c in cookies:
        if c.lower().startswith(f"{name.lower()}="):
            return c
    return None


# ============ AUTH / COOKIES ============
class TestCookieAuth:
    def test_guest_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/guest", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "user" in body and body["user"]["role"] == "guest"
        # cookie jar should now have access_token + refresh_token
        assert s.cookies.get("access_token"), "access_token cookie not set"
        assert s.cookies.get("refresh_token"), "refresh_token cookie not set"
        ac = _has_cookie_set(r, "access_token") or ""
        assert "httponly" in ac.lower(), f"access_token must be HttpOnly. Set-Cookie={ac}"

    def test_login_admin_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200, r.text
        assert s.cookies.get("access_token"), "access_token cookie not set on login"
        assert s.cookies.get("refresh_token"), "refresh_token cookie not set on login"
        body = r.json()
        assert body["user"]["email"] == ADMIN_EMAIL
        assert body["user"]["role"] == "admin"

    def test_register_sets_cookies(self):
        import uuid
        s = requests.Session()
        email = f"TEST_{uuid.uuid4().hex[:8]}@miro.care"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!", "name": "TestU"}, timeout=20)
        assert r.status_code == 200, r.text
        assert s.cookies.get("access_token")
        assert s.cookies.get("refresh_token")
        assert r.json()["user"]["email"] == email.lower()

    def test_me_via_cookie_only(self):
        s = requests.Session()
        s.post(f"{API}/auth/guest", timeout=20)
        # Explicitly remove any Authorization header to ensure cookie path
        r = s.get(f"{API}/auth/me", timeout=20, headers={})
        assert r.status_code == 200, r.text
        assert "user" in r.json()

    def test_me_via_bearer_only(self):
        # login to get access_token JSON; fresh client so no cookie jar leakage
        login = requests.post(
            f"{API}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=20,
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        # Use fresh requests (no cookies)
        r = requests.get(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == ADMIN_EMAIL

    def test_me_no_auth_returns_401(self):
        r = requests.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 401

    def test_logout_clears_cookies(self):
        s = requests.Session()
        s.post(f"{API}/auth/guest", timeout=20)
        assert s.cookies.get("access_token")
        r = s.post(f"{API}/auth/logout", timeout=20)
        assert r.status_code == 200
        # After logout, cookie jar should not have access_token
        assert not s.cookies.get("access_token"), "access_token still in jar after logout"
        assert not s.cookies.get("refresh_token"), "refresh_token still in jar after logout"
        # And /me should now return 401
        r2 = s.get(f"{API}/auth/me", timeout=20)
        assert r2.status_code == 401


# ============ TTS STRICT VOICE ============
class TestTTSStrictVoice:
    PAYLOAD_TEXT = "Привет, как дела сегодня?"

    def _post(self, voice_payload, include_voice=True):
        body = {"text": self.PAYLOAD_TEXT}
        if include_voice:
            body["voice"] = voice_payload
        return requests.post(f"{API}/tts", json=body, timeout=30, stream=True)

    def test_tts_male_200(self):
        r = self._post("male")
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        # consume a tiny bit
        next(r.iter_content(1024), None)
        r.close()

    def test_tts_female_200(self):
        r = self._post("female")
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        next(r.iter_content(1024), None)
        r.close()

    def test_tts_empty_voice_400(self):
        r = self._post("")
        assert r.status_code == 400, f"expected 400 for empty voice, got {r.status_code}: {r.text[:200]}"

    def test_tts_null_voice_400(self):
        # send explicit null
        r = requests.post(f"{API}/tts", json={"text": self.PAYLOAD_TEXT, "voice": None}, timeout=30)
        assert r.status_code == 400, f"expected 400 for voice=null, got {r.status_code}: {r.text[:200]}"

    def test_tts_unknown_voice_400(self):
        r = self._post("unknown")
        assert r.status_code == 400, f"expected 400 for unknown voice, got {r.status_code}: {r.text[:200]}"

    def test_tts_no_voice_param_defaults_male_200(self):
        # No voice key in body — Pydantic Optional default = "male"
        r = self._post(None, include_voice=False)
        assert r.status_code == 200, f"expected 200 (default male), got {r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        r.close()


# ============ CHAT WITH COOKIE-ONLY AUTH ============
class TestChatCookieAuth:
    def test_chat_stream_with_cookie_only(self):
        s = requests.Session()
        guest = s.post(f"{API}/auth/guest", timeout=20)
        assert guest.status_code == 200
        # NO Authorization header → must work via cookie
        import uuid
        session_id = uuid.uuid4().hex
        r = s.post(
            f"{API}/chat/stream",
            json={"message": "Привет", "voice": "male", "session_id": session_id},
            timeout=60,
            stream=True,
            headers={},
        )
        assert r.status_code == 200, r.text[:300]
        # Read SSE stream and verify a 'done' or any data event arrives
        got_data = False
        got_done = False
        for line in r.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line.startswith("data:"):
                got_data = True
            if "done" in (line or "").lower():
                got_done = True
                break
        r.close()
        assert got_data, "No SSE 'data:' frames received from /chat/stream"
        # 'done' is preferred but not strictly required if stream closed cleanly
