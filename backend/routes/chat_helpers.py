"""
Helpers for chat routes — extracted from routes/chat.py to keep that module
focused on HTTP endpoints. Anything in this module is pure-ish business logic:
LLM calls, prompt assembly, search, session bookkeeping, persistence helpers.

Imports are arranged so this module never imports from routes/chat.py — the
dependency direction is one-way: chat.py -> chat_helpers.py.
"""
import os
import re
import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from database import db
from config import SYSTEM_PROMPT, PROBLEMS
from problem_prompts import get_problem_prompt
from crypto_utils import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)


# ============================================================
#                  OPENROUTER CLIENT (lazy)
# ============================================================
_openrouter_client = None


def get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        from openai import AsyncOpenAI
        _openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            default_headers={
                "HTTP-Referer": "https://slimlight.app",
                "X-OpenRouter-Title": "SlimLight",
            },
        )
    return _openrouter_client


# ============================================================
#         IN-MEMORY SESSION HISTORIES (LRU-capped)
# ============================================================
MAX_SESSIONS = 500
chat_histories: "OrderedDict[str, list]" = OrderedDict()
# Photo counter per session — agent knows whether this is photo #1 / #2 / #3+
session_photo_count: "OrderedDict[str, int]" = OrderedDict()


def touch_session(session_id: str) -> None:
    """Mark session as most-recently-used and evict oldest if over cap."""
    if session_id in chat_histories:
        chat_histories.move_to_end(session_id)
    while len(chat_histories) > MAX_SESSIONS:
        chat_histories.popitem(last=False)


# ============================================================
#                      TEXT UTILS
# ============================================================
SEARCH_TAG_RE = re.compile(r'\[SEARCH:\s*(.+?)\]')

# Fish Audio emotion markers (`(calm)`, `[calm]`, `[warm][gentle]`, ...)
# that the LLM sometimes leaks into user-facing text. Strip them — TTS adds its own.
EMOTION_MARKER_RE = re.compile(r'[\(\[]\s*[a-z][a-z\s\-]{0,30}[\)\]]', re.IGNORECASE)


def strip_emotion_markers(text: str) -> str:
    """Remove Fish Audio emotion markers from user-facing text."""
    if not text:
        return text
    cleaned = EMOTION_MARKER_RE.sub('', text)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    cleaned = re.sub(r' +([.,!?…:;])', r'\1', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


SEARCH_INSTRUCTION = """

ИНСТРУМЕНТ ПОИСКА:
Если тебе нужна актуальная информация из интернета (телефон доверия, горячая линия, конкретный факт, ресурс помощи) — напиши в ответе тег:
[SEARCH: запрос]
Например: [SEARCH: телефон доверия Россия]
Система выполнит поиск и даст тебе результаты. После этого ты дашь финальный ответ пользователю.
Используй поиск ТОЛЬКО когда действительно нужна актуальная информация. Не используй для обычного разговора."""


def find_problem_context(problem: Optional[str]) -> str:
    if not problem:
        return ""
    for p in PROBLEMS:
        if p["id"] == problem:
            name_line = f"\n\nПользователь выбрал проблему: {p['name']}. Учитывай это в диалоге."
            return name_line + get_problem_prompt(problem)
    return get_problem_prompt(problem)


def extract_user_name(message: str) -> Optional[str]:
    msg_lower = message.lower().strip()
    for pattern in ["меня зовут ", "я — ", "я - ", "зовите меня ", "my name is ", "i'm ", "i am "]:
        if pattern in msg_lower:
            after = message[msg_lower.index(pattern) + len(pattern):].strip()
            candidate = after.split()[0].strip(".,!?;:") if after else None
            if candidate and 1 < len(candidate) < 30:
                return candidate.capitalize()
    return None


def ddg_search(query: str, max_results: int = 3) -> str:
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "Поиск не дал результатов."
        return "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)
    except Exception as e:
        logger.warning(f"DDG search error: {e}")
        return "Не удалось выполнить поиск."


# ============================================================
#                 LENGTH PROFILES (random per turn)
# ============================================================
import secrets

SHORT_USER_RE = re.compile(
    r'^\s*(да|нет|ага|угу|ок|ок\.|ладно|не\s*знаю|нз|возможно|хм|м+|ok|yes|no)\s*[.!?]*\s*$',
    re.IGNORECASE,
)

LENGTH_PROFILES = {
    "short":  "ОЧЕНЬ КОРОТКО — 1 предложение ИЛИ 3-10 слов. Просто реакция, присутствие, принятие. НЕ задавай вопрос. НЕ делай валидацию + размышление + вопрос. Один выдох — одна фраза.",
    "medium": "СРЕДНЕ — 2-3 коротких предложения максимум. Либо валидация + вопрос, либо размышление + вопрос, но не всё вместе.",
    "long":   "РАЗВЁРНУТО — 4-6 предложений. Валидация + размышление + вопрос-маяк. Используй ТОЛЬКО когда пользователь раскрыл большую/сложную тему, требующую глубины.",
}

LENGTH_TOKEN_LIMITS = {"short": 160, "medium": 400, "long": 900}


def pick_length_mode(user_message: str) -> str:
    """Pick a length profile. Very short replies → short; otherwise weighted random."""
    text = (user_message or "").strip()
    if len(text) <= 12 or SHORT_USER_RE.match(text):
        return "short"
    return secrets.SystemRandom().choices(
        ["short", "medium", "long"],
        weights=[40, 45, 15],
        k=1,
    )[0]


def build_length_directive(mode: str) -> str:
    profile = LENGTH_PROFILES.get(mode, LENGTH_PROFILES["medium"])
    return (
        f"\n\n🔒 СТРОГОЕ ПРАВИЛО ДЛИНЫ ОТВЕТА НА ЭТУ РЕПЛИКУ:\n"
        f"{profile}\n"
        f"Это НЕ пожелание — это жёсткий лимит. Живая беседа звучит именно так: иногда одно слово, иногда фраза.\n"
        f"Не используй структуру «валидация → эмпатия → вопрос» если режим SHORT или MEDIUM."
    )


# ============================================================
#                  OPENROUTER CALLS
# ============================================================
def truncate_to_sentence(text: str) -> str:
    """If response was cut by max_tokens, drop the dangling tail to last terminal punctuation."""
    if not text:
        return text
    last_end = max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind("…"))
    if last_end >= max(40, int(len(text) * 0.5)):
        return text[: last_end + 1].rstrip()
    trimmed = re.sub(r"\s+\S*$", "", text).rstrip(" ,;:-—")
    if trimmed and not trimmed.endswith(("…", ".", "!", "?")):
        trimmed += "…"
    return trimmed or text


def trim_messages(messages: list, max_len: int = 31) -> list:
    """Keep system message + last N messages to stay within context window."""
    if len(messages) > max_len:
        return [messages[0]] + messages[-max_len + 1:]
    return messages


def _wrap_anthropic_cache(messages: list, model: str) -> list:
    """Mark first system message as ephemeral-cached for Anthropic prompt caching."""
    if (
        model.startswith("anthropic/")
        and messages
        and messages[0].get("role") == "system"
        and isinstance(messages[0].get("content"), str)
    ):
        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": messages[0]["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ] + messages[1:]
    return messages


async def call_openrouter(messages: list, model: str = "anthropic/claude-sonnet-4.5", max_tokens: int = 600) -> str:
    client = get_openrouter_client()
    cached_messages = _wrap_anthropic_cache(messages, model)
    try:
        response = await client.chat.completions.create(
            model=model, messages=cached_messages, max_tokens=max_tokens, temperature=0.7,
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        if getattr(choice, "finish_reason", None) == "length":
            text = truncate_to_sentence(text)
        return text
    except Exception as e:
        if model == "anthropic/claude-sonnet-4.5":
            logger.warning(f"Claude Sonnet error, falling back to Mistral: {e}")
            response = await client.chat.completions.create(
                model="mistralai/mistral-small-3.1-24b-instruct",
                messages=messages, max_tokens=max_tokens, temperature=0.7,
            )
            choice = response.choices[0]
            text = choice.message.content or ""
            if getattr(choice, "finish_reason", None) == "length":
                text = truncate_to_sentence(text)
            return text
        raise


async def stream_openrouter(messages: list, model: str = "anthropic/claude-sonnet-4.5", max_tokens: int = 600):
    """Async generator yielding text deltas from OpenRouter streaming completion."""
    client = get_openrouter_client()
    cached_messages = _wrap_anthropic_cache(messages, model)
    stream = await client.chat.completions.create(
        model=model,
        messages=cached_messages,
        max_tokens=max_tokens,
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        try:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
        except (IndexError, AttributeError):
            content = None
        if content:
            yield content


async def handle_search_tag(session_id: str, ai_text: str) -> str:
    """If AI response contains [SEARCH: ...], execute search and get final answer."""
    search_match = SEARCH_TAG_RE.search(ai_text)
    if not search_match:
        return ai_text

    search_query = search_match.group(1).strip()
    logger.info(f"AI requested search: '{search_query}'")
    search_results = ddg_search(search_query)

    chat_histories[session_id].append({"role": "assistant", "content": ai_text})
    chat_histories[session_id].append({
        "role": "user",
        "content": (
            f"[Результаты поиска по запросу '{search_query}']\n{search_results}\n\n"
            "[Используй эти данные чтобы дать финальный ответ пользователю. "
            "НЕ показывай тег [SEARCH]. Дай готовый ответ.]"
        ),
    })

    messages = trim_messages(chat_histories[session_id])
    return await call_openrouter(messages)


# ============================================================
#                 PERSONAL CONTEXT
# ============================================================
async def load_personal_context(user_id: Optional[str]) -> str:
    if not user_id:
        return ""
    try:
        user_doc = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"user_display_name": 1, "session_notes": 1, "current_homework": 1, "current_homework_at": 1}
        )
        if not user_doc:
            return ""
        parts = []
        name = user_doc.get("user_display_name")
        if name:
            parts.append(f"\n\nИмя пользователя: {name}. Обращайся по имени.")
        notes = decrypt_text(user_doc.get("session_notes"))
        if notes:
            parts.append(f"\n\nКонтекст из прошлых сессий: {notes}")
        homework = user_doc.get("current_homework")
        if homework:
            hw_date = user_doc.get("current_homework_at", "")
            parts.append(
                f"\n\n[АКТУАЛЬНОЕ ДОМАШНЕЕ ЗАДАНИЕ пользователя (задано {hw_date}): {homework}]\n"
                "Если это новая сессия — мягко спроси, получилось ли выполнить. "
                "Не навязывай, если пользователь пришёл с новой темой."
            )
        return "".join(parts)
    except Exception:
        return ""


async def init_session(session_id: str, problem: Optional[str], language: str, user_id: Optional[str], voice: Optional[str] = None) -> None:
    """Initialize or update chat session with system prompt."""
    language = language or "en"
    problem_context = find_problem_context(problem)
    personal_context = await load_personal_context(user_id)
    lang_instruction = f"\n\nОтвечай на языке: {language}"

    voice = (voice or "female").lower()
    if voice == "female":
        persona_directive = (
            "🔒 YOUR IDENTITY:\n"
            "Your name is Kylie. You identify as female. In any language with grammatical gender, "
            "speak about yourself in the feminine form.\n"
            "If the user directly asks your name — answer \"My name is Kylie\". Otherwise do not re-introduce yourself.\n"
            "Do NOT announce \"I am a female counselor\" — it is already obvious from context. Just be yourself.\n\n"
        )
    else:
        persona_directive = (
            "🔒 YOUR IDENTITY:\n"
            "Your name is Leon. You identify as male. In any language with grammatical gender, "
            "speak about yourself in the masculine form.\n"
            "If the user directly asks your name — answer \"My name is Leon\". Otherwise do not re-introduce yourself.\n"
            "Do NOT announce \"I am a male counselor\" — it is already obvious from context. Just be yourself.\n\n"
        )

    system_msg = persona_directive + SYSTEM_PROMPT + SEARCH_INSTRUCTION + problem_context + personal_context + lang_instruction

    if session_id in chat_histories:
        chat_histories[session_id][0] = {"role": "system", "content": system_msg}
        touch_session(session_id)
        return

    chat_histories[session_id] = [{"role": "system", "content": system_msg}]
    touch_session(session_id)


async def save_name_if_found(user_id: str, message: str, free_count: int) -> None:
    """Extract and save user name from message if not already set."""
    name_extracted = extract_user_name(message)
    if not name_extracted and len(message.split()) <= 2 and free_count >= 1:
        candidate = message.strip().strip(".,!?;:")
        if candidate and 1 < len(candidate) < 30 and candidate[0].isupper():
            name_extracted = candidate.split()[0]
    if name_extracted:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"user_display_name": name_extracted}}
        )


# ============================================================
#       SESSION NOTES (cross-session memory)
# ============================================================
NOTES_SUMMARY_PROMPT = """Ты — психологический ассистент. На основе диалога создай краткий контекст для следующей сессии.

Напиши 4-6 предложений, включая:
— ключевые темы и проблемы, которые обсуждались
— эмоциональное состояние пользователя (тревога, апатия, норма и т.д.)
— что было предложено или попробовано
— любые важные личные детали, упомянутые пользователем

Пиши лаконично, только факты. Без приветствий и заголовков. Это внутренние заметки для следующего сеанса."""


async def update_session_notes(user_id: str, session_id: str) -> None:
    """Background task: summarise conversation and persist to users.session_notes."""
    try:
        msgs = await db.chat_messages.find(
            {"user_id": user_id, "session_id": session_id},
            {"_id": 0, "user_message": 1, "ai_response": 1, "timestamp": 1},
        ).sort("timestamp", -1).limit(30).to_list(30)

        if not msgs:
            return

        msgs.reverse()
        dialogue_lines = []
        for m in msgs:
            user_msg = decrypt_text(m.get("user_message"))
            ai_resp = decrypt_text(m.get("ai_response"))
            if user_msg and user_msg != "[image]":
                dialogue_lines.append(f"Пользователь: {user_msg}")
            if ai_resp:
                dialogue_lines.append(f"Ассистент: {ai_resp[:300]}")

        if not dialogue_lines:
            return

        dialogue_text = "\n".join(dialogue_lines)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        user_doc = await db.users.find_one({"_id": ObjectId(user_id)}, {"session_notes": 1})
        prev_notes = decrypt_text((user_doc or {}).get("session_notes")) or ""

        summarise_messages = [
            {"role": "system", "content": NOTES_SUMMARY_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Дата сессии: {today}\n\n"
                    f"Диалог:\n{dialogue_text}\n\n"
                    + (f"Контекст предыдущих сессий:\n{prev_notes}\n\n" if prev_notes else "")
                    + "Напиши обновлённые заметки, включая новую информацию из этого диалога."
                ),
            },
        ]

        new_notes = await call_openrouter(summarise_messages, model="anthropic/claude-sonnet-4.5")
        new_notes = new_notes.strip()[:1500]

        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "session_notes": encrypt_text(new_notes),
                "session_notes_updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"Session notes updated for user {user_id} (session {session_id})")
    except Exception as e:
        logger.warning(f"Session notes update failed for user {user_id}: {e}")


# ============================================================
#                  HOMEWORK EXTRACTION
# ============================================================
HOMEWORK_RE = re.compile(
    r"📝\s*(?:на\s+эту\s+неделю|задание|домашнее\s*задание)\s*[:—-]?\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def extract_homework(ai_response: str) -> Optional[str]:
    """Extract homework from AI response using the 📝 marker."""
    if not ai_response or "📝" not in ai_response:
        return None
    m = HOMEWORK_RE.search(ai_response)
    if not m:
        return None
    hw = m.group(1).strip()
    return hw[:400] if hw else None


async def save_homework(user_id: str, homework: str) -> None:
    """Persist homework into the user profile."""
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "current_homework": homework,
                "current_homework_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }},
        )
        logger.info(f"Homework saved for user {user_id}: {homework[:60]}")
    except Exception as e:
        logger.warning(f"save_homework failed for user {user_id}: {e}")


# ============================================================
#                  ACCESS CONTROL
# ============================================================
def check_user_access(user: dict) -> tuple:
    # 🔓 Unlimited: all users — no restrictions.
    free_count = user.get("free_messages_count", 0)
    return True, True, free_count


def build_counter_updates(user: dict, is_free_phase: bool, free_count: int, ai_response: str) -> dict:
    # 🔓 Unlimited: don't increment counters; only persist a plan if AI emitted one.
    update_fields = {}
    if "ПЛАН РАБОТЫ" in ai_response or "PLAN" in ai_response.upper():
        update_fields["last_plan"] = ai_response
    return update_fields


# ============================================================
#       PERSIST USER+AI MESSAGE PAIR (used by /chat & /chat/stream)
# ============================================================
async def persist_chat_turn(
    *,
    user: dict,
    user_id: str,
    req_session_id: str,
    in_memory_session_id: str,
    user_message: str,
    ai_response: str,
    voice: Optional[str],
    problem: Optional[str],
    is_free_phase: bool,
    free_count: int,
) -> None:
    """Persist a single (user + AI) chat turn to MongoDB and trigger background tasks
    (name extraction, session-notes summarisation, homework extraction)."""
    await db.chat_messages.insert_one({
        "user_id": user_id,
        "session_id": req_session_id,
        "user_message": encrypt_text(user_message),
        "ai_response": encrypt_text(ai_response),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "problem": problem or user.get("selected_problem"),
        "voice": voice or user.get("selected_voice") or "male",
    })

    if not user.get("user_display_name"):
        await save_name_if_found(user_id, user_message, free_count)

    update_fields = build_counter_updates(user, is_free_phase, free_count, ai_response)
    if update_fields:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

    user_msg_count = sum(
        1 for m in chat_histories.get(in_memory_session_id, []) if m.get("role") == "user"
    )
    if user_msg_count > 0 and user_msg_count % 6 == 0:
        asyncio.create_task(update_session_notes(user_id, req_session_id))

    homework = extract_homework(ai_response)
    if homework:
        asyncio.create_task(save_homework(user_id, homework))
