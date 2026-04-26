"""
Chat routes: /chat, /chat/image, /chat/history, /chat/sessions
Includes AI logic (OpenRouter + DuckDuckGo search).
"""
import os
import re
import json
import secrets
import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId

from database import db
from auth_utils import get_current_user
from config import SYSTEM_PROMPT, PROBLEMS
from problem_prompts import get_problem_prompt
from crypto_utils import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------- OPENROUTER CLIENT (lazy import to speed up cold start) ----------
_openrouter_client = None


def get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        from openai import AsyncOpenAI
        _openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            default_headers={
                "HTTP-Referer": "https://miro.care",
                "X-OpenRouter-Title": "Miro.Care",
            },
        )
    return _openrouter_client

# ---------- IN-MEMORY SESSION HISTORIES (LRU-capped) ----------
MAX_SESSIONS = 500
chat_histories: "OrderedDict[str, list]" = OrderedDict()
# Счётчик фото в сессии — чтобы агент знал: это 1-е/2-е/3+ фото для сравнения
session_photo_count: "OrderedDict[str, int]" = OrderedDict()


def _touch_session(session_id: str) -> None:
    """Mark session as most-recently-used and evict oldest if over cap."""
    if session_id in chat_histories:
        chat_histories.move_to_end(session_id)
    while len(chat_histories) > MAX_SESSIONS:
        chat_histories.popitem(last=False)

# ---------- MODELS ----------
class ChatRequest(BaseModel):
    message: str
    session_id: str
    agent_id: Optional[str] = None
    language: Optional[str] = "ru"
    problem: Optional[str] = None
    voice: Optional[str] = None  # "male" (Leon) | "female" (Kylie) — для корректного рода в ответе


class ChatImageRequest(BaseModel):
    session_id: str
    image: str
    language: Optional[str] = "ru"
    problem: Optional[str] = None


# ---------- HELPERS ----------
SEARCH_TAG_RE = re.compile(r'\[SEARCH:\s*(.+?)\]')

# Маркеры эмоций Fish Audio (`(calm)`, `[calm]`, `[warm][gentle]`, ...),
# которые LLM иногда вставляет в ответ, хотя это служебные теги для TTS.
# Вырезаем их из текста, который уходит пользователю — TTS добавит свои в tts.py.
# Матчит короткие ASCII-фразы в круглых/квадратных скобках (поддержка S1 и S2-Pro).
EMOTION_MARKER_RE = re.compile(r'[\(\[]\s*[a-z][a-z\s\-]{0,30}[\)\]]', re.IGNORECASE)


def strip_emotion_markers(text: str) -> str:
    """Убирает Fish Audio emotion-маркеры из текста для пользователя."""
    if not text:
        return text
    cleaned = EMOTION_MARKER_RE.sub('', text)
    # Схлопываем лишние пробелы, появившиеся после удаления маркеров
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
    # Имя проблемы + полный методический под-промпт (КПТ / ACT / EFT / …)
    for p in PROBLEMS:
        if p["id"] == problem:
            name_line = f"\n\nПользователь выбрал проблему: {p['name']}. Учитывай это в диалоге."
            return name_line + get_problem_prompt(problem)
    return get_problem_prompt(problem)


# ---------- DYNAMIC RESPONSE LENGTH ----------
# Случайный выбор режима длины, чтобы ответы не были однообразными, как в живой беседе.
SHORT_USER_RE = re.compile(r'^\s*(да|нет|ага|угу|ок|ок\.|ладно|не\s*знаю|нз|возможно|хм|м+|ok|yes|no)\s*[.!?]*\s*$', re.IGNORECASE)

LENGTH_PROFILES = {
    "short":  "ОЧЕНЬ КОРОТКО — 1 предложение ИЛИ 3-10 слов. Просто реакция, присутствие, принятие. НЕ задавай вопрос. НЕ делай валидацию + размышление + вопрос. Один выдох — одна фраза.",
    "medium": "СРЕДНЕ — 2-3 коротких предложения максимум. Либо валидация + вопрос, либо размышление + вопрос, но не всё вместе.",
    "long":   "РАЗВЁРНУТО — 4-6 предложений. Валидация + размышление + вопрос-маяк. Используй ТОЛЬКО когда пользователь раскрыл большую/сложную тему, требующую глубины.",
}

# Лимиты токенов под каждый режим — с запасом, чтобы модель не обрывала фразу посреди слова,
# если она чуть превысила ориентир длины. Реальная длина всё равно ограничена директивой в промпте.
LENGTH_TOKEN_LIMITS = {"short": 160, "medium": 400, "long": 900}


def pick_length_mode(user_message: str) -> str:
    """Выбирает ориентир длины. Короткие реплики → short; иначе случайный выбор с распределением."""
    text = (user_message or "").strip()

    # Очень короткая / односложная реплика пользователя → всегда short
    if len(text) <= 12 or SHORT_USER_RE.match(text):
        return "short"

    # Распределение, имитирующее живую беседу: больше short/medium, long — редко.
    # Используем SystemRandom (CSPRNG) — не критично для безопасности, но снимает шум линтера S311.
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
            parts.append(f"\n\n[АКТУАЛЬНОЕ ДОМАШНЕЕ ЗАДАНИЕ пользователя (задано {hw_date}): {homework}]\nЕсли это новая сессия — мягко спроси, получилось ли выполнить. Не навязывай, если пользователь пришёл с новой темой.")
        return "".join(parts)
    except Exception:
        return ""


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


async def call_openrouter(messages: list, model: str = "anthropic/claude-sonnet-4.5", max_tokens: int = 600) -> str:
    client = get_openrouter_client()
    # Prompt caching для Anthropic: помечаем первое system-сообщение как кэшируемое.
    # OpenRouter пробрасывает cache_control в Anthropic, что экономит до 90% токенов system-промпта
    # при повторных вызовах в течение 5 минут.
    cached_messages = messages
    if model.startswith("anthropic/") and messages and messages[0].get("role") == "system" and isinstance(messages[0].get("content"), str):
        cached_messages = [
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
    try:
        response = await client.chat.completions.create(
            model=model, messages=cached_messages, max_tokens=max_tokens, temperature=0.7,
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)
        # Если модель упёрлась в max_tokens и оборвала предложение посреди слова —
        # аккуратно обрезаем текст до последнего законченного предложения.
        if finish_reason == "length":
            text = _truncate_to_sentence(text)
        return text
    except Exception as e:
        if model == "anthropic/claude-sonnet-4.5":
            logger.warning(f"Claude Sonnet error, falling back to Mistral: {e}")
            # Mistral не поддерживает cache_control — передаём plain messages.
            response = await client.chat.completions.create(
                model="mistralai/mistral-small-3.1-24b-instruct",
                messages=messages, max_tokens=max_tokens, temperature=0.7,
            )
            choice = response.choices[0]
            text = choice.message.content or ""
            if getattr(choice, "finish_reason", None) == "length":
                text = _truncate_to_sentence(text)
            return text
        raise

async def stream_openrouter(messages: list, model: str = "anthropic/claude-sonnet-4.5", max_tokens: int = 600):
    """Async generator yielding text deltas from OpenRouter streaming completion."""
    client = get_openrouter_client()
    cached_messages = messages
    if (
        model.startswith("anthropic/")
        and messages
        and messages[0].get("role") == "system"
        and isinstance(messages[0].get("content"), str)
    ):
        cached_messages = [
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




def _truncate_to_sentence(text: str) -> str:
    """Если ответ был обрезан по max_tokens, откусываем «висящий» хвост до последнего
    завершающего знака (.!?…). Если такого знака нет — ставим многоточие в конце,
    чтобы не оставлять пользователя с половиной слова."""
    if not text:
        return text
    # Ищем последний терминальный знак препинания.
    last_end = max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind("…"))
    if last_end >= max(40, int(len(text) * 0.5)):
        return text[: last_end + 1].rstrip()
    # Иначе — обрезаем последнее незаконченное слово и ставим многоточие.
    trimmed = re.sub(r"\s+\S*$", "", text).rstrip(" ,;:-—")
    if trimmed and not trimmed.endswith(("…", ".", "!", "?")):
        trimmed += "…"
    return trimmed or text


def _trim_messages(messages: list, max_len: int = 31) -> list:
    """Keep system message + last N messages to stay within context window."""
    if len(messages) > max_len:
        return [messages[0]] + messages[-max_len + 1:]
    return messages


async def _handle_search_tag(session_id: str, ai_text: str) -> str:
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

    messages = _trim_messages(chat_histories[session_id])
    return await call_openrouter(messages)


async def _init_session(session_id: str, problem: Optional[str], language: str, user_id: Optional[str], voice: Optional[str] = None) -> None:
    """Initialize or update chat session with system prompt."""
    language = language or "en"
    problem_context = find_problem_context(problem)
    personal_context = await load_personal_context(user_id)
    lang_instruction = f"\n\nОтвечай на языке: {language}"

    # Gender / persona directive — keeps Leon (male) and Kylie (female) consistent across languages.
    # Placed at the very start of the system prompt — Claude best follows the first instructions.
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
        # Update system prompt if language/voice changed
        chat_histories[session_id][0] = {"role": "system", "content": system_msg}
        _touch_session(session_id)
        return

    chat_histories[session_id] = [{"role": "system", "content": system_msg}]
    _touch_session(session_id)


async def _save_name_if_found(user_id: str, message: str, free_count: int) -> None:
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


# ---------- SESSION NOTES (cross-session memory) ----------
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


# ---------- HOMEWORK EXTRACTION ----------
# Паттерн: «📝 На эту неделю:...», «📝 Задание:...», «📝 Домашнее задание:...»
HOMEWORK_RE = re.compile(r"📝\s*(?:на\s+эту\s+неделю|задание|домашнее\s*задание)\s*[:—-]?\s*(.+)", re.IGNORECASE | re.DOTALL)


def extract_homework(ai_response: str) -> Optional[str]:
    """Извлекает домашнее задание из ответа ИИ по маркеру 📝."""
    if not ai_response or "📝" not in ai_response:
        return None
    m = HOMEWORK_RE.search(ai_response)
    if not m:
        return None
    hw = m.group(1).strip()
    # Обрезаем слишком длинные (больше 400 символов — это не задание, а монолог)
    return hw[:400] if hw else None


async def save_homework(user_id: str, homework: str) -> None:
    """Сохраняет домашнее задание в профиле пользователя."""
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


def check_user_access(user: dict) -> tuple:
    # 🔓 Безлимит: все пользователи без ограничений
    free_count = user.get("free_messages_count", 0)
    return True, True, free_count


def build_counter_updates(user: dict, is_free_phase: bool, free_count: int, ai_response: str) -> dict:
    # 🔓 Безлимит: счётчики не инкрементируем, только сохраняем план если есть
    update_fields = {}
    if "ПЛАН РАБОТЫ" in ai_response or "PLAN" in ai_response.upper():
        update_fields["last_plan"] = ai_response
    return update_fields


# ---------- ENDPOINTS ----------
@router.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    # Мягкая авторизация — как в Xicon.online
    try:
        user = await get_current_user(request)
    except Exception:
        # Без токена — работаем анонимно
        user = {"_id": None, "free_messages_count": 0, "minutes_left": 999, "is_paid_session_active": True, "selected_language": "ru"}
    user_id = user["_id"]

    is_free_phase, has_minutes, free_count = check_user_access(user)
    if not is_free_phase and not has_minutes:
        return {
            "message": "Ваши бесплатные сообщения закончились. Пожалуйста, выберите тариф для продолжения.",
            "type": "tariff_prompt",
            "needs_tariff": True,
        }

    session_id = f"{user_id or 'anon'}_{req.session_id}"
    try:
        await _init_session(
            session_id,
            req.problem or user.get("selected_problem"),
            req.language or user.get("selected_language", "ru"),
            user_id,
            req.voice or user.get("selected_voice") or "male",
        )

        chat_histories[session_id].append({"role": "user", "content": req.message})

        # Динамическая длина — случайное чередование short/medium/long как в живой беседе.
        length_mode = pick_length_mode(req.message)
        length_hint = build_length_directive(length_mode)
        max_tokens = LENGTH_TOKEN_LIMITS.get(length_mode, 220)
        base_messages = _trim_messages(chat_histories[session_id])
        messages = [dict(m) for m in base_messages]
        # Модифицируем первое system-сообщение — добавляем ориентир длины в конец.
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = messages[0]["content"] + length_hint

        ai_response = await call_openrouter(messages, max_tokens=max_tokens)
        logger.info(f"CHAT | session={session_id} | length_mode={length_mode} | tokens_cap={max_tokens} | resp_len={len(ai_response)}")
        ai_response = await _handle_search_tag(session_id, ai_response)
        ai_response = strip_emotion_markers(ai_response)
        chat_histories[session_id].append({"role": "assistant", "content": ai_response})

        # DB операции только для авторизованных (не анонимов)
        if user_id:
            await db.chat_messages.insert_one({
                "user_id": user_id,
                "session_id": req.session_id,
                "user_message": encrypt_text(req.message),
                "ai_response": encrypt_text(ai_response),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "problem": req.problem or user.get("selected_problem"),
                "voice": req.voice or user.get("selected_voice") or "male",
            })

            if not user.get("user_display_name"):
                await _save_name_if_found(user_id, req.message, free_count)

            update_fields = build_counter_updates(user, is_free_phase, free_count, ai_response)
            if update_fields:
                await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

            user_msg_count = sum(1 for m in chat_histories.get(session_id, []) if m.get("role") == "user")
            if user_msg_count > 0 and user_msg_count % 6 == 0:
                asyncio.create_task(update_session_notes(user_id, req.session_id))

            # Извлекаем и сохраняем домашнее задание, если ИИ его предложил.
            homework = extract_homework(ai_response)
            if homework:
                asyncio.create_task(save_homework(user_id, homework))

        return {
            "message": ai_response,
            "type": "ai_response",
            "needs_tariff": False,
            "minutes_left": None,
            "is_free_phase": True,
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        err_str = str(e)
        # Bubble up a cleaner message for unconfigured/invalid provider keys
        if "401" in err_str or "No cookie auth credentials" in err_str or "Unauthorized" in err_str:
            raise HTTPException(503, "AI provider key not configured. Please set OPENROUTER_API_KEY.")
        raise HTTPException(500, f"Chat error: {err_str}")


@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest, request: Request):
    """SSE streaming variant of /chat. Streams Claude tokens as they arrive.
    Frontend accumulates text and dispatches sentence-by-sentence TTS in parallel.

    Event format (one per line, JSON):
      data: {"type":"delta","text":"..."}
      data: {"type":"done","full_text":"..."}
      data: {"type":"error","message":"..."}
    """
    try:
        user = await get_current_user(request)
    except Exception:
        user = {"_id": None, "free_messages_count": 0, "minutes_left": 999, "is_paid_session_active": True, "selected_language": "ru"}
    user_id = user["_id"]

    is_free_phase, has_minutes, free_count = check_user_access(user)
    if not is_free_phase and not has_minutes:
        async def gated():
            payload = {"type": "tariff_prompt", "message": "Ваши бесплатные сообщения закончились. Пожалуйста, выберите тариф для продолжения."}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(gated(), media_type="text/event-stream")

    session_id = f"{user_id or 'anon'}_{req.session_id}"
    await _init_session(
        session_id,
        req.problem or user.get("selected_problem"),
        req.language or user.get("selected_language", "ru"),
        user_id,
        req.voice or user.get("selected_voice") or "male",
    )

    chat_histories[session_id].append({"role": "user", "content": req.message})

    length_mode = pick_length_mode(req.message)
    length_hint = build_length_directive(length_mode)
    max_tokens = LENGTH_TOKEN_LIMITS.get(length_mode, 220)
    base_messages = _trim_messages(chat_histories[session_id])
    messages = [dict(m) for m in base_messages]
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = messages[0]["content"] + length_hint

    async def event_gen():
        full_text_parts = []
        try:
            async for delta in stream_openrouter(messages, max_tokens=max_tokens):
                full_text_parts.append(delta)
                yield f"data: {json.dumps({'type': 'delta', 'text': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            # Fallback to non-streaming Mistral on Claude failure
            try:
                fallback_text = await call_openrouter(messages, model="mistralai/mistral-small-3.1-24b-instruct", max_tokens=max_tokens)
                full_text_parts = [fallback_text]
                yield f"data: {json.dumps({'type': 'delta', 'text': fallback_text}, ensure_ascii=False)}\n\n"
            except Exception as e2:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e2)}, ensure_ascii=False)}\n\n"
                return

        full_text = "".join(full_text_parts)
        # Handle [SEARCH:] tag if present
        if SEARCH_TAG_RE.search(full_text):
            search_resolved = await _handle_search_tag(session_id, full_text)
            full_text = search_resolved
            yield f"data: {json.dumps({'type': 'replace', 'text': full_text}, ensure_ascii=False)}\n\n"

        full_text = strip_emotion_markers(full_text)
        chat_histories[session_id].append({"role": "assistant", "content": full_text})

        # Persist + bookkeeping
        if user_id:
            try:
                await db.chat_messages.insert_one({
                    "user_id": user_id,
                    "session_id": req.session_id,
                    "user_message": encrypt_text(req.message),
                    "ai_response": encrypt_text(full_text),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "problem": req.problem or user.get("selected_problem"),
                    "voice": req.voice or user.get("selected_voice") or "male",
                })
                if not user.get("user_display_name"):
                    await _save_name_if_found(user_id, req.message, free_count)
                update_fields = build_counter_updates(user, is_free_phase, free_count, full_text)
                if update_fields:
                    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

                user_msg_count = sum(1 for m in chat_histories.get(session_id, []) if m.get("role") == "user")
                if user_msg_count > 0 and user_msg_count % 6 == 0:
                    asyncio.create_task(update_session_notes(user_id, req.session_id))

                homework = extract_homework(full_text)
                if homework:
                    asyncio.create_task(save_homework(user_id, homework))
            except Exception as e:
                logger.warning(f"Stream persistence failed: {e}")

        yield f"data: {json.dumps({'type': 'done', 'full_text': full_text}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/image")
async def chat_image_endpoint(req: ChatImageRequest, request: Request):
    try:
        user = await get_current_user(request)
    except Exception:
        user = {"_id": None, "free_messages_count": 0, "minutes_left": 999, "is_paid_session_active": True, "selected_language": "ru"}
    user_id = user["_id"]

    is_free_phase, has_minutes, free_count = check_user_access(user)
    if not is_free_phase and not has_minutes:
        return {
            "response": "Ваши бесплатные сообщения закончились. Пожалуйста, выберите тариф.",
            "type": "tariff_prompt",
            "needs_tariff": True,
        }

    session_id = f"{user_id or 'anon'}_{req.session_id}"
    lang = req.language or user.get("selected_language", "ru")

    await _init_session(session_id, req.problem or user.get("selected_problem"), lang, user_id, user.get("selected_voice") or "male")
    chat_histories[session_id].append({"role": "user", "content": "[Пользователь отправил фото]"})

    # Счётчик фото в этой сессии (1-е / 2-е / 3+ — агент подстраивает анализ)
    photo_count = session_photo_count.get(session_id, 0) + 1
    session_photo_count[session_id] = photo_count
    # LRU-eviction для счётчика фото
    while len(session_photo_count) > MAX_SESSIONS:
        session_photo_count.popitem(last=False)

    if photo_count == 1:
        photo_directive = (
            "Это ПЕРВОЕ фото клиента в этой сессии. "
            "Действуй по блоку «АНАЛИЗ ФОТО → ОДНО ФОТО»: "
            "оцени общее телосложение, зоны накопления жира, осанку, связь с анкетой. "
            "Ответ без осуждения, без медицинских терминов, конкретно. "
            "В конце мягко спроси: «Есть фото где вес был заметно другим? Если да — пришлите, интересно посмотреть на динамику.»"
        )
    elif photo_count == 2:
        photo_directive = (
            "Это ВТОРОЕ фото в этой сессии. "
            "Действуй по блоку «АНАЛИЗ ФОТО → ВТОРОЕ ФОТО (сравнение)»: "
            "сравни с тем что уже видел, отметь позитивные изменения первыми, "
            "не акцентируй на негативе. В конце дай один конкретный шаг под выявленную зону."
        )
    else:
        photo_directive = (
            f"Это УЖЕ {photo_count}-е фото в этой сессии. "
            "Действуй по блоку «АНАЛИЗ ФОТО → ТРИ И БОЛЬШЕ ФОТО»: "
            "выбери два наиболее контрастных фото из увиденных и сравни их, как со «вторым фото»."
        )

    vision_msg = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{req.image}"}},
            {
                "type": "text",
                "text": (
                    f"Клиент прислал фото. Проанализируй согласно инструкции. {photo_directive} "
                    f"Отвечай на языке: {lang}. "
                    "Не комментируй одежду и фон. Если фото нечёткое — попроси прислать другое."
                ),
            },
        ],
    }

    messages = chat_histories[session_id][:-1] + [vision_msg]
    messages = _trim_messages(messages)

    try:
        ai_text = await call_openrouter(messages)
    except Exception as e:
        logger.error(f"Image chat error: {e}")
        try:
            fallback_msgs = [m for m in chat_histories[session_id] if isinstance(m.get("content"), str)]
            fallback_msgs.append({
                "role": "user",
                "content": f"Пользователь отправил фото. Поблагодари за доверие и спроси, что на фото. Отвечай на языке: {lang}",
            })
            ai_text = await call_openrouter(fallback_msgs[-20:], model="mistralai/mistral-small-3.1-24b-instruct")
        except Exception as e2:
            logger.error(f"Image chat fallback error: {e2}")
            raise HTTPException(500, f"Image analysis error: {str(e)}")

    ai_text = strip_emotion_markers(ai_text)
    chat_histories[session_id].append({"role": "assistant", "content": ai_text})

    if user_id:
        await db.chat_messages.insert_one({
            "user_id": user_id,
            "session_id": req.session_id,
            "user_message": "[image]",
            "ai_response": encrypt_text(ai_text),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "problem": req.problem or user.get("selected_problem"),
        })

        update_fields = build_counter_updates(user, is_free_phase, free_count, ai_text)
        if update_fields:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

    return {
        "response": ai_text,
        "type": "ai_response",
        "needs_tariff": False,
    }


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, request: Request):
    user = await get_current_user(request)
    messages = await db.chat_messages.find(
        {"user_id": user["_id"], "session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(200)
    # Расшифровываем контент диалога перед отдачей клиенту
    for m in messages:
        if "user_message" in m:
            m["user_message"] = decrypt_text(m["user_message"])
        if "ai_response" in m:
            m["ai_response"] = decrypt_text(m["ai_response"])
    return {"messages": messages}


@router.get("/chat/notes")
async def get_session_notes(request: Request):
    user = await get_current_user(request)
    doc = await db.users.find_one(
        {"_id": ObjectId(user["_id"])},
        {"_id": 0, "session_notes": 1, "session_notes_updated_at": 1},
    )
    return {
        "notes": decrypt_text((doc or {}).get("session_notes")) or "",
        "updated_at": (doc or {}).get("session_notes_updated_at") or None,
    }


@router.delete("/chat/notes")
async def clear_session_notes(request: Request):
    user = await get_current_user(request)
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$unset": {"session_notes": "", "session_notes_updated_at": ""}},
    )
    return {"message": "Session notes cleared"}


@router.get("/chat/sessions")
async def get_chat_sessions(request: Request):
    user = await get_current_user(request)
    pipeline = [
        {"$match": {"user_id": user["_id"]}},
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$session_id",
            "last_timestamp": {"$first": "$timestamp"},
            "last_message": {"$first": "$user_message"},
            "message_count": {"$sum": 1},
        }},
        {"$sort": {"last_timestamp": -1}},
        {"$limit": 10},
    ]
    sessions = await db.chat_messages.aggregate(pipeline).to_list(10)
    return {"sessions": [
        {
            "session_id": s["_id"],
            "last_timestamp": s["last_timestamp"],
            "preview": (decrypt_text(s.get("last_message")) or "")[:60],
            "count": s["message_count"],
        }
        for s in sessions
    ]}



@router.delete("/chat/messages")
async def clear_chat_messages(request: Request):
    """Clear all chat messages for the current user. Keeps user profile, settings, and questionnaire intact."""
    user = await get_current_user(request)
    result = await db.chat_messages.delete_many({"user_id": user["_id"]})
    # Drop in-memory session histories belonging to this user too.
    sessions_to_drop = []
    for sid, hist in chat_histories.items():
        if any(m.get("_user_id") == user["_id"] for m in hist if isinstance(m, dict)):
            sessions_to_drop.append(sid)
    for sid in sessions_to_drop:
        chat_histories.pop(sid, None)
        session_photo_count.pop(sid, None)
    return {"message": "Chat messages cleared", "deleted": result.deleted_count}


class SpecialistRequestPayload(BaseModel):
    name: Optional[str] = None
    contact: str
    note: Optional[str] = None
    channel: Optional[str] = None  # "whatsapp" | "phone" | "form"


@router.post("/specialist/request")
async def specialist_request(payload: SpecialistRequestPayload, request: Request):
    """Persist a 'Talk to a Specialist' request. Lightweight intake — only contact + optional note."""
    user = await get_current_user(request)
    doc = {
        "user_id": user["_id"],
        "name": (payload.name or "").strip()[:120] or None,
        "contact": payload.contact.strip()[:200],
        "note": (payload.note or "").strip()[:1000] or None,
        "channel": payload.channel or "form",
        "status": "new",
        "created_at": datetime.now(timezone.utc),
    }
    await db.specialist_requests.insert_one(doc)
    return {"message": "Request received"}
