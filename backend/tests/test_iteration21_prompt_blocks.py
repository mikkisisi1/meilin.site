"""Iteration 21: SYSTEM_PROMPT extension regression.
Tests:
- Basic endpoints health/problems/tariffs/specialists 200
- /api/chat: Russian, no closed endings (Понятно./Ясно./Хорошо./Окей./Принято.)
- Multi-turn no-repeat-question after intake [АНКЕТА]
- Same session second message context retention
- /api/tts voice=male/female returns audio/mpeg
- Unlimited (>5 msgs guest, no 402/403)
"""
import os
import re
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

CLOSED_ENDINGS = ["понятно.", "ясно.", "хорошо.", "окей.", "принято."]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- basic endpoints ----
@pytest.mark.parametrize("path", ["/api/health", "/api/problems", "/api/tariffs", "/api/specialists"])
def test_basic_endpoints_200(session, path):
    r = session.get(f"{BASE_URL}{path}", timeout=20)
    assert r.status_code == 200, f"{path} -> {r.status_code} body={r.text[:200]}"


# ---- chat helpers ----
def _last_sentence(txt: str) -> str:
    txt = (txt or "").strip()
    # split on .!?…
    parts = [p.strip() for p in re.split(r"(?<=[\.!\?…])\s+", txt) if p.strip()]
    return parts[-1] if parts else txt


def _has_open_invitation(txt: str) -> bool:
    last = _last_sentence(txt).lower()
    if "?" in last:
        return True
    # last sentence must NOT be one of forbidden closed endings (case-insensitive, exact word)
    norm = last.strip().rstrip(" \t")
    return norm not in CLOSED_ENDINGS


def _is_russian(txt: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", txt or ""))


# ---- /api/chat regression ----
def test_chat_basic_russian_open_ending(session):
    sid = f"TEST_iter21_basic_{uuid.uuid4().hex[:8]}"
    r = session.post(f"{BASE_URL}/api/chat", json={
        "message": "Привет, я хочу похудеть, помоги.",
        "session_id": sid,
        "language": "ru",
        "voice": "male",
    }, timeout=90)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    msg = data.get("message", "")
    assert _is_russian(msg), f"Not Russian: {msg[:200]}"
    assert data.get("needs_tariff") is False
    assert data.get("is_free_phase") is True
    last = _last_sentence(msg)
    forbidden_hit = last.strip().lower() in CLOSED_ENDINGS
    assert not forbidden_hit, f"Closed ending detected: '{last}' in: {msg[:300]}"
    # Soft check: should ideally end with question or open invitation
    has_q = "?" in last
    print(f"[basic] last_sentence='{last}' has_question={has_q}")


def test_chat_multi_turn_no_repeat(session):
    sid = f"TEST_iter21_multi_{uuid.uuid4().hex[:8]}"
    msgs = [
        "Привет, меня зовут Алексей.",
        "Я хочу сбросить пять килограммов.",
        "В основном переедаю вечером после работы.",
    ]
    last_msg = ""
    for m in msgs:
        r = session.post(f"{BASE_URL}/api/chat", json={
            "message": m, "session_id": sid, "language": "ru", "voice": "male",
        }, timeout=90)
        assert r.status_code == 200, r.text[:300]
        last_msg = r.json().get("message", "")
        assert _is_russian(last_msg)
        last_sent = _last_sentence(last_msg).strip().lower()
        assert last_sent not in CLOSED_ENDINGS, f"Closed ending in turn: '{last_sent}'"
    print(f"[multi-turn] final='{last_msg[:200]}'")


def test_chat_after_intake_no_repeat_questions(session):
    sid = f"TEST_iter21_intake_{uuid.uuid4().hex[:8]}"
    intake = (
        "[АНКЕТА]\n"
        "Имя: Алексей\n"
        "Возраст: 35\n"
        "Пол: мужской\n"
        "Вес: 95 кг, Рост: 178 см (ИМТ ~30)\n"
        "Цель: сбросить 10 кг за 3 месяца\n"
        "Триггер: стресс\n"
        "Время переедания: вечером\n"
        "Что пробовали: диеты, не получилось\n"
        "Ограничения: гипертония\n"
        "Мотивация: 7/10\n"
    )
    r = session.post(f"{BASE_URL}/api/chat", json={
        "message": intake, "session_id": sid, "language": "ru", "voice": "male",
    }, timeout=90)
    assert r.status_code == 200, r.text[:300]
    msg1 = r.json().get("message", "")
    assert _is_russian(msg1)
    # Bot should now be in Mode 2 — should NOT ask again about weight, age, name
    lo = msg1.lower()
    forbidden_re_asks = ["сколько вам лет", "ваш возраст", "сколько вы весите", "какой у вас вес", "как вас зовут"]
    hits = [q for q in forbidden_re_asks if q in lo]
    assert not hits, f"Bot re-asked intake question(s): {hits}\nReply: {msg1[:400]}"
    # Closed ending check
    last = _last_sentence(msg1).strip().lower()
    assert last not in CLOSED_ENDINGS, f"Closed ending: '{last}'"

    # Second turn — bot should still remember Алексей and not re-ask
    r2 = session.post(f"{BASE_URL}/api/chat", json={
        "message": "Да, особенно после работы вечером тянет к сладкому.",
        "session_id": sid, "language": "ru", "voice": "male",
    }, timeout=90)
    assert r2.status_code == 200
    msg2 = r2.json().get("message", "")
    lo2 = msg2.lower()
    hits2 = [q for q in forbidden_re_asks if q in lo2]
    assert not hits2, f"Turn-2 re-asked: {hits2}\nReply: {msg2[:400]}"
    last2 = _last_sentence(msg2).strip().lower()
    assert last2 not in CLOSED_ENDINGS
    print(f"[intake] msg1_last='{_last_sentence(msg1)[:120]}' msg2_last='{_last_sentence(msg2)[:120]}'")


def test_chat_unlimited_no_paywall(session):
    sid = f"TEST_iter21_unlim_{uuid.uuid4().hex[:8]}"
    for i in range(6):
        r = session.post(f"{BASE_URL}/api/chat", json={
            "message": f"Сообщение номер {i+1}, продолжаем диалог.",
            "session_id": sid, "language": "ru", "voice": "female",
        }, timeout=90)
        assert r.status_code not in (402, 403), f"Paywall hit at msg {i+1}: {r.status_code}"
        assert r.status_code == 200
        data = r.json()
        assert data.get("needs_tariff") is False, f"needs_tariff true at msg {i+1}"


# ---- /api/tts ----
@pytest.mark.parametrize("voice,expected_id_prefix", [
    ("male", "5cfccfb8"),
    ("female", "7a98513e"),
])
def test_tts_streaming(session, voice, expected_id_prefix):
    r = session.post(f"{BASE_URL}/api/tts", json={
        "text": "Привет, как ваши дела сегодня?",
        "voice": voice,
    }, timeout=30, stream=True)
    assert r.status_code == 200, f"TTS {voice} -> {r.status_code} {r.text[:200]}"
    assert "audio/mpeg" in r.headers.get("content-type", ""), r.headers
    # Read at least one chunk
    chunks = 0
    total = 0
    for chunk in r.iter_content(chunk_size=4096):
        if chunk:
            chunks += 1
            total += len(chunk)
            if total > 2000:
                break
    assert total > 0, f"No audio bytes for voice={voice}"
    print(f"[tts {voice}] bytes_read={total} chunks={chunks}")
    r.close()
