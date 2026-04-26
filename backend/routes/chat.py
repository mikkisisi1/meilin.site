"""
Chat HTTP endpoints. Business logic (LLM calls, prompt assembly, search,
session bookkeeping, persistence) lives in routes/chat_helpers.py.

Endpoints:
  POST   /chat              — synchronous chat
  POST   /chat/stream       — SSE streaming chat
  POST   /chat/image        — vision/photo chat
  GET    /chat/history/{id} — fetch message history
  GET    /chat/notes        — get session-notes summary
  DELETE /chat/notes        — clear session-notes summary
  GET    /chat/sessions     — list user's recent sessions
  DELETE /chat/messages     — clear all messages for current user
  POST   /specialist/request — submit a "Talk to a Specialist" request
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user
from crypto_utils import decrypt_text

from routes.chat_helpers import (
    # session bookkeeping
    chat_histories,
    session_photo_count,
    MAX_SESSIONS,
    init_session,
    # llm
    call_openrouter,
    stream_openrouter,
    handle_search_tag,
    trim_messages,
    # text utils
    strip_emotion_markers,
    SEARCH_TAG_RE,
    # length
    pick_length_mode,
    build_length_directive,
    LENGTH_TOKEN_LIMITS,
    # access + persistence
    check_user_access,
    persist_chat_turn,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- MODELS ----------
class ChatRequest(BaseModel):
    message: str
    session_id: str
    agent_id: Optional[str] = None
    language: Optional[str] = "ru"
    problem: Optional[str] = None
    voice: Optional[str] = None  # "male" (Leon) | "female" (Kylie)


class ChatImageRequest(BaseModel):
    session_id: str
    image: str
    language: Optional[str] = "ru"
    problem: Optional[str] = None


class SpecialistRequestPayload(BaseModel):
    name: Optional[str] = None
    contact: str
    note: Optional[str] = None
    channel: Optional[str] = None  # "whatsapp" | "phone" | "form"


_ANON_USER = {
    "_id": None,
    "free_messages_count": 0,
    "minutes_left": 999,
    "is_paid_session_active": True,
    "selected_language": "ru",
}


async def _resolve_user(request: Request) -> dict:
    """Soft-auth: return real user if cookie is valid, else anonymous shell."""
    try:
        return await get_current_user(request)
    except Exception:
        return dict(_ANON_USER)


def _prepare_messages(session_id: str, user_message: str) -> tuple[list, str, int]:
    """Append user msg, pick length profile, return (messages, mode, max_tokens)."""
    chat_histories[session_id].append({"role": "user", "content": user_message})
    length_mode = pick_length_mode(user_message)
    length_hint = build_length_directive(length_mode)
    max_tokens = LENGTH_TOKEN_LIMITS.get(length_mode, 220)

    base_messages = trim_messages(chat_histories[session_id])
    messages = [dict(m) for m in base_messages]
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = messages[0]["content"] + length_hint
    return messages, length_mode, max_tokens


# ============================================================
#                       /chat (sync)
# ============================================================
@router.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    user = await _resolve_user(request)
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
        await init_session(
            session_id,
            req.problem or user.get("selected_problem"),
            req.language or user.get("selected_language", "ru"),
            user_id,
            req.voice or user.get("selected_voice") or "male",
        )

        messages, length_mode, max_tokens = _prepare_messages(session_id, req.message)

        ai_response = await call_openrouter(messages, max_tokens=max_tokens)
        logger.info(
            f"CHAT | session={session_id} | length_mode={length_mode} "
            f"| tokens_cap={max_tokens} | resp_len={len(ai_response)}"
        )
        ai_response = await handle_search_tag(session_id, ai_response)
        ai_response = strip_emotion_markers(ai_response)
        chat_histories[session_id].append({"role": "assistant", "content": ai_response})

        if user_id:
            await persist_chat_turn(
                user=user,
                user_id=user_id,
                req_session_id=req.session_id,
                in_memory_session_id=session_id,
                user_message=req.message,
                ai_response=ai_response,
                voice=req.voice,
                problem=req.problem,
                is_free_phase=is_free_phase,
                free_count=free_count,
            )

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
        if "401" in err_str or "No cookie auth credentials" in err_str or "Unauthorized" in err_str:
            raise HTTPException(503, "AI provider key not configured. Please set OPENROUTER_API_KEY.")
        raise HTTPException(500, f"Chat error: {err_str}")


# ============================================================
#                  /chat/stream (SSE)
# ============================================================
@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest, request: Request):
    """SSE streaming variant of /chat. Streams Claude tokens as they arrive.

    Event format (one per line, JSON):
      data: {"type":"delta","text":"..."}
      data: {"type":"done","full_text":"..."}
      data: {"type":"error","message":"..."}
    """
    user = await _resolve_user(request)
    user_id = user["_id"]

    is_free_phase, has_minutes, free_count = check_user_access(user)
    if not is_free_phase and not has_minutes:
        async def gated():
            payload = {
                "type": "tariff_prompt",
                "message": "Ваши бесплатные сообщения закончились. Пожалуйста, выберите тариф для продолжения.",
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(gated(), media_type="text/event-stream")

    session_id = f"{user_id or 'anon'}_{req.session_id}"
    await init_session(
        session_id,
        req.problem or user.get("selected_problem"),
        req.language or user.get("selected_language", "ru"),
        user_id,
        req.voice or user.get("selected_voice") or "male",
    )

    messages, _length_mode, max_tokens = _prepare_messages(session_id, req.message)

    async def event_gen():
        full_text_parts = []
        try:
            async for delta in stream_openrouter(messages, max_tokens=max_tokens):
                full_text_parts.append(delta)
                yield f"data: {json.dumps({'type': 'delta', 'text': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            try:
                fallback_text = await call_openrouter(
                    messages, model="mistralai/mistral-small-3.1-24b-instruct", max_tokens=max_tokens
                )
                full_text_parts = [fallback_text]
                yield f"data: {json.dumps({'type': 'delta', 'text': fallback_text}, ensure_ascii=False)}\n\n"
            except Exception as e2:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e2)}, ensure_ascii=False)}\n\n"
                return

        full_text = "".join(full_text_parts)
        if SEARCH_TAG_RE.search(full_text):
            full_text = await handle_search_tag(session_id, full_text)
            yield f"data: {json.dumps({'type': 'replace', 'text': full_text}, ensure_ascii=False)}\n\n"

        full_text = strip_emotion_markers(full_text)
        chat_histories[session_id].append({"role": "assistant", "content": full_text})

        if user_id:
            try:
                await persist_chat_turn(
                    user=user,
                    user_id=user_id,
                    req_session_id=req.session_id,
                    in_memory_session_id=session_id,
                    user_message=req.message,
                    ai_response=full_text,
                    voice=req.voice,
                    problem=req.problem,
                    is_free_phase=is_free_phase,
                    free_count=free_count,
                )
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


# ============================================================
#                  /chat/image (vision)
# ============================================================
def _photo_directive(photo_count: int) -> str:
    if photo_count == 1:
        return (
            "Это ПЕРВОЕ фото клиента в этой сессии. "
            "Действуй по блоку «АНАЛИЗ ФОТО → ОДНО ФОТО»: "
            "оцени общее телосложение, зоны накопления жира, осанку, связь с анкетой. "
            "Ответ без осуждения, без медицинских терминов, конкретно. "
            "В конце мягко спроси: «Есть фото где вес был заметно другим? Если да — пришлите, интересно посмотреть на динамику.»"
        )
    if photo_count == 2:
        return (
            "Это ВТОРОЕ фото в этой сессии. "
            "Действуй по блоку «АНАЛИЗ ФОТО → ВТОРОЕ ФОТО (сравнение)»: "
            "сравни с тем что уже видел, отметь позитивные изменения первыми, "
            "не акцентируй на негативе. В конце дай один конкретный шаг под выявленную зону."
        )
    return (
        f"Это УЖЕ {photo_count}-е фото в этой сессии. "
        "Действуй по блоку «АНАЛИЗ ФОТО → ТРИ И БОЛЬШЕ ФОТО»: "
        "выбери два наиболее контрастных фото из увиденных и сравни их, как со «вторым фото»."
    )


@router.post("/chat/image")
async def chat_image_endpoint(req: ChatImageRequest, request: Request):
    user = await _resolve_user(request)
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

    await init_session(
        session_id,
        req.problem or user.get("selected_problem"),
        lang,
        user_id,
        user.get("selected_voice") or "male",
    )
    chat_histories[session_id].append({"role": "user", "content": "[Пользователь отправил фото]"})

    photo_count = session_photo_count.get(session_id, 0) + 1
    session_photo_count[session_id] = photo_count
    while len(session_photo_count) > MAX_SESSIONS:
        session_photo_count.popitem(last=False)

    photo_directive = _photo_directive(photo_count)

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
    messages = trim_messages(messages)

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
        from crypto_utils import encrypt_text
        await db.chat_messages.insert_one({
            "user_id": user_id,
            "session_id": req.session_id,
            "user_message": "[image]",
            "ai_response": encrypt_text(ai_text),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "problem": req.problem or user.get("selected_problem"),
        })

        from routes.chat_helpers import build_counter_updates
        update_fields = build_counter_updates(user, is_free_phase, free_count, ai_text)
        if update_fields:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})

    return {
        "response": ai_text,
        "type": "ai_response",
        "needs_tariff": False,
    }


# ============================================================
#               READ-ONLY HISTORY / NOTES / SESSIONS
# ============================================================
@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, request: Request):
    user = await get_current_user(request)
    messages = await db.chat_messages.find(
        {"user_id": user["_id"], "session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(200)
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
    sessions_to_drop = []
    for sid, hist in chat_histories.items():
        if any(m.get("_user_id") == user["_id"] for m in hist if isinstance(m, dict)):
            sessions_to_drop.append(sid)
    for sid in sessions_to_drop:
        chat_histories.pop(sid, None)
        session_photo_count.pop(sid, None)
    return {"message": "Chat messages cleared", "deleted": result.deleted_count}


# ============================================================
#                /specialist/request
# ============================================================
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
