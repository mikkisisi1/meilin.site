"""
Magic-link auth: /auth/magic/request and /auth/magic/verify.

Flow:
  1. Frontend collects an email or phone, POST /auth/magic/request.
  2. Backend mints a `secrets.token_urlsafe(32)` token, stores it with TTL 24h,
     attaches it to the current user (if authenticated) or to a freshly-created
     user keyed by email/phone, then dispatches the link via notifications.py.
  3. User clicks the link → frontend `/magic/:token` page → POST /auth/magic/verify.
  4. Backend verifies single-use, sets httpOnly cookies via `set_auth_cookies`,
     returns the user. Frontend redirects to `/chat`.
"""
import os
import re
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from bson import ObjectId

from database import db
from auth_utils import (
    create_access_token, create_refresh_token,
    set_auth_cookies, get_current_user,
)
from notifications import send_magic_link

logger = logging.getLogger(__name__)
router = APIRouter()

TOKEN_TTL_HOURS = 24
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")  # E.164


def _public_origin() -> str:
    """Where the magic link should send the user — must match what the browser
    sees, so we read PUBLIC_ORIGIN first, then fall back to FRONTEND_URL."""
    return (
        os.environ.get("PUBLIC_ORIGIN")
        or os.environ.get("FRONTEND_URL")
        or "https://leon-kylie-chat.preview.emergentagent.com"
    ).rstrip("/")


class MagicRequestModel(BaseModel):
    channel: Literal["email", "whatsapp"]
    destination: str  # email or E.164 phone


class MagicVerifyModel(BaseModel):
    token: str


@router.post("/auth/magic/request")
async def magic_request(req: MagicRequestModel, request: Request):
    dest = req.destination.strip()
    if req.channel == "email":
        if not EMAIL_RE.match(dest):
            raise HTTPException(400, "Invalid email")
        dest = dest.lower()
        user_query = {"email": dest}
        user_patch_on_create = {"email": dest}
    else:
        if not PHONE_RE.match(dest):
            raise HTTPException(400, "Invalid phone (use E.164 like +14155550123)")
        user_query = {"phone": dest}
        user_patch_on_create = {"phone": dest}

    # If the caller is already authenticated (e.g. a guest who just finished
    # intake), promote that account by attaching the email/phone — preserves
    # their chat history. Otherwise upsert on email/phone.
    current_user_id: Optional[str] = None
    try:
        current = await get_current_user(request)
        if current.get("role") == "guest":
            current_user_id = current["_id"]
    except HTTPException:
        current_user_id = None

    if current_user_id:
        # Promote the guest to a "real" user since they've claimed a contact —
        # is_guest=False so the AuthPromptModal won't keep nagging on revisits,
        # but their existing chat history (linked to user_id) stays intact.
        await db.users.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": {**user_patch_on_create, "role": "user", "is_guest": False}},
        )
        user_id = current_user_id
    else:
        existing = await db.users.find_one(user_query)
        if existing:
            user_id = str(existing["_id"])
        else:
            now_iso = datetime.now(timezone.utc).isoformat()
            doc = {
                "password_hash": "",
                "name": user_patch_on_create.get("email", "").split("@")[0] or "User",
                "role": "user",
                "created_at": now_iso,
                "tariff": None,
                "minutes_total": 0,
                "minutes_used": 0,
                "minutes_left": 0,
                "tariff_expires_at": None,
                "test_used": False,
                "selected_problem": None,
                "selected_voice": None,
                "selected_language": "en",
                "theme": "system",
                "last_plan": None,
                "is_paid_session_active": False,
                "free_messages_count": 0,
                **user_patch_on_create,
            }
            res = await db.users.insert_one(doc)
            user_id = str(res.inserted_id)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    await db.magic_tokens.insert_one({
        "token": token,
        "user_id": user_id,
        "channel": req.channel,
        "destination": dest,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })

    link = f"{_public_origin()}/magic/{token}"
    try:
        await send_magic_link(channel=req.channel, destination=dest, link=link)
    except Exception as e:
        logger.error(f"Magic-link dispatch failed (still issued): {e}")

    return {"status": "sent", "channel": req.channel}


@router.post("/auth/magic/verify")
async def magic_verify(req: MagicVerifyModel, response: Response):
    rec = await db.magic_tokens.find_one({"token": req.token}, {"_id": 0})
    if not rec:
        raise HTTPException(400, "Invalid or expired link")
    if rec.get("used"):
        raise HTTPException(400, "This link was already used")
    expires_at = rec["expires_at"]
    if expires_at.tzinfo is None:  # Mongo can return naive
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "This link has expired")

    await db.magic_tokens.update_one(
        {"token": req.token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}},
    )

    user = await db.users.find_one({"_id": ObjectId(rec["user_id"])})
    if not user:
        raise HTTPException(400, "User not found")

    user_id = str(user["_id"])
    access = create_access_token(user_id, user.get("email") or user.get("phone") or "")
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)

    user["_id"] = user_id
    user.pop("password_hash", None)
    return {"user": user, "access_token": access}
