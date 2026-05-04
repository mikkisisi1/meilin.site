"""
Iteration 17 tests:
1. Chat truncation (no mid-word cut)
2. Multilingual chat (ru, en, es, fr, de, zh, ar, hi)
3. Gender switching between agents (male/female)
4. Confidentiality prompt section
5. At-rest encryption (ENC1:: prefix in MongoDB, decrypted via /chat/history)
6. Encryption backward compatibility (plaintext records return as-is)
7. TTS for male/female voices (audio/mpeg, MP3 header)
"""
import os
import uuid
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://slimlight-debug.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "miro_care")

VALID_ENDINGS = (".", "!", "?", "…", "»", '"', ")", "。", "？", "！", "؟", "।")


def _unique_email():
    return f"TEST_iter17_{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    yield client[DB_NAME]
    client.close()


def _reset_quota(mongo_db, user_id):
    """Reset user's chat quota so tests don't hit tariff prompt."""
    from bson import ObjectId
    mongo_db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"free_messages_count": 0, "minutes_left": 9999, "minutes_used": 0}},
    )


@pytest.fixture(scope="module")
def auth_user(mongo_db):
    """Create a fresh registered user and return (token, user_id, email)."""
    email = _unique_email()
    pwd = "TestPass2026!"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": pwd, "name": "TEST User"}, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token in register response: {data}"
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r2.status_code == 200
    me = r2.json()
    # /api/auth/me returns { "user": { "_id": "...", ... } } — _id is already a string
    user_obj = me.get("user") or me
    user_id = user_obj.get("_id") or user_obj.get("id")
    user = {"token": token, "user_id": user_id, "email": email}
    _reset_quota(mongo_db, user_id)
    return user


@pytest.fixture(autouse=True)
def reset_before_test(request, mongo_db):
    """Reset quota before each chat test to avoid tariff prompts."""
    # Only reset if test uses auth_user fixture
    if "auth_user" in request.fixturenames:
        user = request.getfixturevalue("auth_user")
        _reset_quota(mongo_db, user["user_id"])
    yield


def _auth_headers(user):
    return {"Authorization": f"Bearer {user['token']}", "Content-Type": "application/json"}


# ---------- 1. Truncation (no mid-word cut) ----------
class TestTruncation:
    def test_ten_responses_end_properly(self, auth_user):
        prompts = [
            "Привет",
            "Да",
            "Расскажи про тревогу, у меня она последнюю неделю каждый день",
            "Ок",
            "Я ничего не чувствую уже месяц, как будто внутри пусто",
            "Мне плохо в отношениях, партнёр постоянно критикует и я не знаю что делать",
            "Угу",
            "У меня был сложный день, устала очень",
            "Как мне справиться с паникой когда она накрывает в метро, подскажи подробно",
            "Что мне делать если я всё время себя критикую за любую мелочь",
        ]
        bad = []
        for i, p in enumerate(prompts):
            sid = f"TEST_trunc_{uuid.uuid4().hex[:8]}"
            r = requests.post(f"{BASE_URL}/api/chat",
                              headers=_auth_headers(auth_user),
                              json={"message": p, "session_id": sid, "language": "ru", "voice": "male"},
                              timeout=90)
            assert r.status_code == 200, f"chat failed [{i}]: {r.status_code} {r.text[:200]}"
            msg = (r.json().get("message") or "").strip()
            assert msg, f"Empty response for prompt[{i}]"
            if not msg.endswith(VALID_ENDINGS):
                bad.append((i, p, msg[-50:]))
        assert not bad, f"Responses not ending cleanly: {bad}"


# ---------- 2. Multilingual ----------
class TestMultilingual:
    LANG_PROMPTS = {
        "ru": "Мне тревожно последние дни, не могу спать",
        "en": "I feel very anxious these days and can't sleep well",
        "es": "Me siento muy ansioso estos días y no puedo dormir",
        "fr": "Je me sens très anxieux ces jours-ci et je n'arrive pas à dormir",
        "de": "Ich fühle mich in letzter Zeit sehr ängstlich und kann nicht schlafen",
        "zh": "我最近感到很焦虑,晚上睡不着",
        "ar": "أشعر بقلق شديد هذه الأيام ولا أستطيع النوم",
        "hi": "मुझे इन दिनों बहुत चिंता हो रही है और नींद नहीं आती",
    }

    def test_each_language(self, auth_user):
        failures = []
        for lang, prompt in self.LANG_PROMPTS.items():
            sid = f"TEST_lang_{lang}_{uuid.uuid4().hex[:6]}"
            r = requests.post(f"{BASE_URL}/api/chat",
                              headers=_auth_headers(auth_user),
                              json={"message": prompt, "session_id": sid, "language": lang, "voice": "male"},
                              timeout=90)
            if r.status_code != 200:
                failures.append((lang, r.status_code, r.text[:150]))
                continue
            msg = (r.json().get("message") or "").strip()
            if not msg:
                failures.append((lang, "empty", ""))
            elif not msg.endswith(VALID_ENDINGS):
                failures.append((lang, "no-clean-end", msg[-40:]))
        assert not failures, f"Multilingual failures: {failures}"


# ---------- 3. Gender switching ----------
class TestGenderSwitch:
    MALE_MARKERS = ["я рад", "я понял", "я услышал", "я подумал", "я хотел"]
    FEMALE_MARKERS = ["я рада", "я поняла", "я услышала", "я подумала", "я хотела"]

    def _ask_gender(self, auth_user, voice, session_suffix):
        sid = f"TEST_gen_{session_suffix}_{uuid.uuid4().hex[:6]}"
        prompt = "Скажи про себя одну фразу начинающуюся со слова 'Я' — например 'Я рад тебя слышать' или 'Я поняла тебя'. Используй прошедшее время."
        r = requests.post(f"{BASE_URL}/api/chat",
                          headers=_auth_headers(auth_user),
                          json={"message": prompt, "session_id": sid, "language": "ru", "voice": voice},
                          timeout=90)
        assert r.status_code == 200, f"chat failed: {r.status_code} {r.text[:200]}"
        return (r.json().get("message") or "").lower()

    def test_male_then_female(self, auth_user):
        male_resp = self._ask_gender(auth_user, "male", "m1")
        female_resp = self._ask_gender(auth_user, "female", "f1")

        male_has_male = any(m in male_resp for m in self.MALE_MARKERS)
        male_has_female = any(m in male_resp for m in self.FEMALE_MARKERS)
        female_has_female = any(m in female_resp for m in self.FEMALE_MARKERS)
        female_has_male = any(m in female_resp for m in self.MALE_MARKERS)

        # Soft assertion: Miron should not use female forms AND Oksana should use female forms
        assert not (male_has_female and not male_has_male), (
            f"Miron (male) uses female forms: {male_resp[:300]}"
        )
        assert female_has_female or not female_has_male, (
            f"Oksana (female) doesn't use female forms: {female_resp[:300]}"
        )


# ---------- 4. Confidentiality ----------
class TestConfidentiality:
    def test_confidentiality_question(self, auth_user):
        sid = f"TEST_conf_{uuid.uuid4().hex[:8]}"
        r = requests.post(f"{BASE_URL}/api/chat",
                          headers=_auth_headers(auth_user),
                          json={"message": "Насколько наш диалог конфиденциальный? Кто может его прочитать?",
                                "session_id": sid, "language": "ru", "voice": "female"},
                          timeout=90)
        assert r.status_code == 200
        msg = (r.json().get("message") or "").lower()
        # Must touch on protection/privacy
        keywords = ["конфиден", "защищ", "зашифр", "между", "только", "никто", "доступ", "безопас", "личн"]
        hits = [k for k in keywords if k in msg]
        assert len(hits) >= 2, f"Confidentiality answer lacks privacy keywords: {msg[:400]}"


# ---------- 5. Encryption at rest ----------
class TestEncryptionAtRest:
    def test_enc_prefix_in_mongo_and_decrypted_via_api(self, auth_user, mongo_db):
        sid = f"TEST_enc_{uuid.uuid4().hex[:10]}"
        unique_phrase = f"секретная-фраза-{uuid.uuid4().hex[:8]}"
        r = requests.post(f"{BASE_URL}/api/chat",
                          headers=_auth_headers(auth_user),
                          json={"message": unique_phrase, "session_id": sid, "language": "ru", "voice": "male"},
                          timeout=90)
        assert r.status_code == 200
        time.sleep(0.5)

        # Check MongoDB — raw records must have ENC1:: prefix
        doc = mongo_db.chat_messages.find_one({"session_id": sid})
        assert doc is not None, "Chat message not found in MongoDB"
        assert isinstance(doc.get("user_message"), str), "user_message not a string"
        assert doc["user_message"].startswith("ENC1::"), f"user_message not encrypted: {doc['user_message'][:50]}"
        assert doc["ai_response"].startswith("ENC1::"), f"ai_response not encrypted: {doc['ai_response'][:50]}"
        # Plaintext must NOT be in raw doc
        assert unique_phrase not in doc["user_message"], "Plaintext leaked in raw user_message"

        # GET /api/chat/history/{sid} must return decrypted
        r2 = requests.get(f"{BASE_URL}/api/chat/history/{sid}",
                          headers=_auth_headers(auth_user), timeout=30)
        assert r2.status_code == 200
        msgs = r2.json().get("messages", [])
        assert len(msgs) >= 1
        assert msgs[0]["user_message"] == unique_phrase, (
            f"History did not return decrypted plaintext: {msgs[0]['user_message'][:60]}"
        )
        assert not msgs[0]["user_message"].startswith("ENC1::"), "History returned encrypted data"

    def test_backward_compat_plaintext(self, auth_user, mongo_db):
        """Insert a plaintext record directly and verify /chat/history returns it as-is."""
        sid = f"TEST_legacy_{uuid.uuid4().hex[:10]}"
        legacy_text = f"legacy-plaintext-{uuid.uuid4().hex[:6]}"
        mongo_db.chat_messages.insert_one({
            "user_id": auth_user["user_id"],
            "session_id": sid,
            "user_message": legacy_text,
            "ai_response": "legacy ai response",
            "timestamp": "2024-01-01T00:00:00+00:00",
        })
        r = requests.get(f"{BASE_URL}/api/chat/history/{sid}",
                         headers=_auth_headers(auth_user), timeout=30)
        assert r.status_code == 200
        msgs = r.json().get("messages", [])
        assert len(msgs) >= 1
        assert msgs[0]["user_message"] == legacy_text, f"legacy plaintext mangled: {msgs[0]}"
        assert msgs[0]["ai_response"] == "legacy ai response"
        # Cleanup
        mongo_db.chat_messages.delete_many({"session_id": sid})


# ---------- 6. TTS ----------
class TestTTS:
    def _check_tts(self, text, voice, lang="ru"):
        r = requests.post(f"{BASE_URL}/api/tts",
                          json={"text": text, "voice": voice, "language": lang},
                          timeout=60)
        assert r.status_code == 200, f"TTS {voice}/{lang} failed: {r.status_code} {r.text[:150]}"
        ct = r.headers.get("content-type", "").lower()
        assert "audio/mpeg" in ct or "audio" in ct, f"Unexpected content-type: {ct}"
        content = r.content
        assert len(content) > 1000, f"Audio too small: {len(content)} bytes"
        # MP3 header: ID3 or 0xFF 0xFB/0xF3/0xF2
        is_mp3 = content[:3] == b"ID3" or (content[0] == 0xFF and (content[1] & 0xE0) == 0xE0)
        assert is_mp3, f"Not valid MP3 header: {content[:8].hex()}"

    def test_male_ru(self):
        self._check_tts("Привет, я Мирон. Я здесь чтобы выслушать тебя.", "male", "ru")

    def test_female_ru(self):
        self._check_tts("Привет, я Оксана. Я рада тебя слышать.", "female", "ru")

    def test_male_en(self):
        self._check_tts("Hello, I am Miron, a psychologist. How can I help?", "male", "en")

    def test_female_en(self):
        self._check_tts("Hello, I am Oksana, I am glad to hear you.", "female", "en")
