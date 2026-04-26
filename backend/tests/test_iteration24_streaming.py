"""
Iteration 24: tests for /api/chat/stream SSE endpoint, /api/chat voice persistence,
and config updates (warm emotion marker + system prompt style line).
"""
import os
import json
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://slim-you-1.preview.emergentagent.com").rstrip("/")


def _parse_sse(raw_text: str):
    events = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
            events.append(payload)
        except json.JSONDecodeError:
            pass
    return events


# ---------- Streaming endpoint ----------
class TestChatStream:
    def test_stream_anonymous_returns_sse_with_deltas_and_done(self):
        url = f"{BASE_URL}/api/chat/stream"
        payload = {
            "message": "Привет, как тебя зовут?",
            "session_id": f"TEST_iter24_stream_{int(time.time())}",
            "language": "ru",
            "voice": "male",
        }
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            assert resp.status_code == 200, resp.text
            ct = resp.headers.get("content-type", "")
            assert "text/event-stream" in ct, f"Wrong content-type: {ct}"
            body = resp.text
        events = _parse_sse(body)
        deltas = [e for e in events if e.get("type") == "delta"]
        dones = [e for e in events if e.get("type") == "done"]
        assert len(deltas) >= 2, f"Expected >=2 delta events, got {len(deltas)}"
        assert len(dones) == 1, f"Expected exactly 1 done event, got {len(dones)}"
        delta_concat = "".join(d.get("text", "") for d in deltas)
        full_text = dones[0].get("full_text", "")
        assert full_text, "done.full_text empty"
        # Concat may equal full_text OR full_text may be post-processed (emotion markers stripped)
        # so we check that full_text length is close to or shorter than concat
        assert len(full_text) > 0
        # Loose check: some non-empty intersection
        assert len(full_text) <= len(delta_concat) + 10

    def test_stream_voice_male_responds_as_leon(self):
        url = f"{BASE_URL}/api/chat/stream"
        payload = {
            "message": "Как тебя зовут? Ответь одним предложением.",
            "session_id": f"TEST_iter24_male_{int(time.time())}",
            "language": "ru",
            "voice": "male",
        }
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            assert resp.status_code == 200
            body = resp.text
        events = _parse_sse(body)
        dones = [e for e in events if e.get("type") == "done"]
        assert dones, "no done event"
        full = dones[0].get("full_text", "").lower()
        # Leon should reference "leon" or "леон"
        assert "leon" in full or "леон" in full, f"Leon not in response: {full}"

    def test_stream_voice_female_responds_as_kylie(self):
        url = f"{BASE_URL}/api/chat/stream"
        payload = {
            "message": "Как тебя зовут? Ответь одним предложением.",
            "session_id": f"TEST_iter24_female_{int(time.time())}",
            "language": "ru",
            "voice": "female",
        }
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            assert resp.status_code == 200
            body = resp.text
        events = _parse_sse(body)
        dones = [e for e in events if e.get("type") == "done"]
        assert dones, "no done event"
        full = dones[0].get("full_text", "").lower()
        assert "kylie" in full or "кайли" in full or "кайлі" in full, f"Kylie not in response: {full}"


# ---------- Non-streaming chat preserves voice ----------
class TestChatNonStreaming:
    def test_chat_returns_200_and_message(self):
        url = f"{BASE_URL}/api/chat"
        payload = {
            "message": "Привет",
            "session_id": f"TEST_iter24_classic_{int(time.time())}",
            "language": "ru",
            "voice": "male",
        }
        r = requests.post(url, json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "message" in data
        assert isinstance(data["message"], str) and len(data["message"]) > 0
        assert data.get("type") == "ai_response"


# ---------- Config updates ----------
class TestConfigUpdates:
    def test_voice_config_emotion_marker_includes_warm(self):
        from voice_config import EMOTION_MARKERS
        base = EMOTION_MARKERS.get("base", "")
        assert "[warm]" in base, f"[warm] missing from base: {base}"
        # Sanity: still has calm + professional + attentive
        assert "[calm]" in base
        assert "[professional]" in base
        assert "[attentive]" in base

    def test_system_prompt_contains_warm_style_line(self):
        from config import SYSTEM_PROMPT
        # Russian style line: "спокойный, профессиональный, внимательный, тёплый"
        assert "спокойный" in SYSTEM_PROMPT
        assert "профессиональный" in SYSTEM_PROMPT
        assert "внимательный" in SYSTEM_PROMPT
        assert "тёплый" in SYSTEM_PROMPT
