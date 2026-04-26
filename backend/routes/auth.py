"""
Auth & user-settings routes: /auth/* and /user/*
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

from database import db
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, set_auth_cookies,
)
from config import TARIFFS, PROBLEMS

router = APIRouter()


# ---------- MODELS ----------
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class VoiceUpdateRequest(BaseModel):
    voice: str


class ProblemUpdateRequest(BaseModel):
    problem: str


class LanguageUpdateRequest(BaseModel):
    language: str


class ThemeUpdateRequest(BaseModel):
    theme: str


# ---------- AUTH ENDPOINTS ----------
@router.post("/auth/guest")
async def create_guest(response: Response):
    guest_id = uuid.uuid4().hex[:8]
    guest_email = f"guest_{guest_id}@demo.slimlight.app"
    user_doc = {
        "email": guest_email,
        "password_hash": "",
        "name": "Guest",
        "role": "guest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tariff": None,
        "minutes_total": 0,
        "minutes_used": 0,
        "minutes_left": 0,
        "tariff_expires_at": None,
        "test_used": False,
        "selected_problem": None,
        "selected_voice": None,
        "selected_language": "ru",
        "theme": "system",
        "last_plan": None,
        "is_paid_session_active": False,
        "free_messages_count": 0,
        "is_guest": True,
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access_token = create_access_token(user_id, guest_email)
    refresh_token = create_refresh_token(user_id)
    set_auth_cookies(response, access_token, refresh_token)
    user_doc["_id"] = user_id
    user_doc.pop("password_hash")
    return {"user": user_doc, "access_token": access_token}


@router.post("/auth/register")
async def register(req: RegisterRequest, response: Response):
    email = req.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user_doc = {
        "email": email,
        "password_hash": hash_password(req.password),
        "name": req.name or email.split("@")[0],
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tariff": None,
        "minutes_total": 0,
        "minutes_used": 0,
        "minutes_left": 0,
        "tariff_expires_at": None,
        "test_used": False,
        "selected_problem": None,
        "selected_voice": None,
        "selected_language": "ru",
        "theme": "system",
        "last_plan": None,
        "is_paid_session_active": False,
        "free_messages_count": 0,
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    set_auth_cookies(response, access_token, refresh_token)
    user_doc["_id"] = user_id
    user_doc.pop("password_hash")
    return {"user": user_doc, "access_token": access_token}


@router.post("/auth/login")
async def login(req: LoginRequest, response: Response):
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    set_auth_cookies(response, access_token, refresh_token)
    user["_id"] = user_id
    user.pop("password_hash", None)
    return {"user": user, "access_token": access_token}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {"user": user}


# ---------- USER SETTINGS ----------
@router.put("/user/voice")
async def update_voice(req: VoiceUpdateRequest, request: Request):
    user = await get_current_user(request)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"selected_voice": req.voice}})
    return {"message": "Voice updated"}


@router.put("/user/problem")
async def update_problem(req: ProblemUpdateRequest, request: Request):
    user = await get_current_user(request)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"selected_problem": req.problem}})
    return {"message": "Problem updated"}


@router.put("/user/language")
async def update_language(req: LanguageUpdateRequest, request: Request):
    user = await get_current_user(request)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"selected_language": req.language}})
    return {"message": "Language updated"}


@router.put("/user/theme")
async def update_theme(req: ThemeUpdateRequest, request: Request):
    user = await get_current_user(request)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"theme": req.theme}})
    return {"message": "Theme updated"}


# ---------- LOOKUP DATA ----------
@router.get("/problems")
async def get_problems():
    return {"problems": PROBLEMS}


@router.get("/tariffs")
async def get_tariffs():
    return {"tariffs": TARIFFS}
