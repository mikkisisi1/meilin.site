from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from database import client, db
from auth_utils import hash_password
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.tts import router as tts_router
from routes.payments import router as payments_router
from routes.bookings import router as bookings_router
from routes.stt import router as stt_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Miro.Care API")


# ---------- HEALTH CHECK (K8s readiness/liveness probes) ----------
@app.get("/")
@app.get("/health")
@app.get("/healthz")
@app.get("/ready")
@app.get("/readyz")
@app.get("/api")
@app.get("/api/")
@app.get("/api/health")
@app.get("/api/healthz")
async def health():
    return {"status": "ok"}


api_router = APIRouter(prefix="/api")

# Mount all route modules
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(tts_router)
api_router.include_router(payments_router)
api_router.include_router(bookings_router)
api_router.include_router(stt_router)


# ---------- STARTUP / SHUTDOWN ----------
async def _bg_init():
    """Non-blocking background init so K8s health probes pass immediately."""
    try:
        await db.users.create_index("email", unique=True)
        await seed_admin()
        logger.info("Miro.Care backend init complete")
    except Exception as e:
        logger.error(f"Background init failed (will retry on demand): {e}")


@app.on_event("startup")
async def startup():
    # Kick off DB init in the background so uvicorn marks the app ready immediately.
    asyncio.create_task(_bg_init())
    logger.info("Miro.Care backend started (bg init dispatched)")


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@miro.care")
    admin_password = os.environ.get("ADMIN_PASSWORD", "MiroCare2026!")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tariff": "month",
            "minutes_total": 99999,
            "minutes_used": 0,
            "minutes_left": 99999,
            "test_used": False,
            "selected_problem": None,
            "selected_voice": None,
            "selected_language": "ru",
            "theme": "system",
            "last_plan": None,
            "is_paid_session_active": True,
            "free_messages_count": 0,
        })
        logger.info(f"Admin user created: {admin_email}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ---------- CORS & ROUTER ----------
app.include_router(api_router)

# Static greetings (pre-rendered MP3 in Kylie/Leon voice, served via CDN cache)
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
frontend_url = os.environ.get("FRONTEND_URL", "")
if frontend_url and frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
