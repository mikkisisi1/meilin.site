"""
Bookings & Specialists routes: /bookings/*, /specialists
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import db
from auth_utils import get_current_user
from config import BOOKING_PRICE, BOOKING_ADVANCE_PERCENT, BOOKING_SLOTS, SPECIALISTS

logger = logging.getLogger(__name__)
router = APIRouter()


class BookingRequest(BaseModel):
    date: str       # YYYY-MM-DD
    time_slot: str  # e.g. "13:00"


# ---------- SPECIALISTS ----------
@router.get("/specialists")
async def get_specialists(problem: str = None):
    if problem:
        filtered = [s for s in SPECIALISTS if problem in s.get("specialization", [])]
        return {"specialists": filtered if filtered else SPECIALISTS}
    return {"specialists": SPECIALISTS}


# ---------- BOOKING SLOTS ----------
@router.get("/bookings/slots")
async def get_booking_slots(request: Request):
    user = await get_current_user(request)
    user_id = user["_id"]

    now_utc = datetime.now(timezone.utc)
    now_moscow = now_utc + timedelta(hours=3)
    today = now_moscow.date()

    start_date = today.isoformat()
    end_date = (today + timedelta(days=30)).isoformat()

    booked_cursor = db.bookings.find(
        {"date": {"$gte": start_date, "$lte": end_date}, "status": {"$in": ["booked", "confirmed"]}},
        {"_id": 0, "date": 1, "time_slot": 1, "user_id": 1, "status": 1},
    )
    booked_list = await booked_cursor.to_list(500)

    booked_map = {
        f"{b['date']}_{b['time_slot']}": {"user_id": b.get("user_id"), "status": b.get("status")}
        for b in booked_list
    }

    calendar = []
    for day_offset in range(31):
        d = today + timedelta(days=day_offset)
        if d.weekday() >= 5:  # skip Sat/Sun
            continue
        day_slots = []
        for slot in BOOKING_SLOTS:
            key = f"{d.isoformat()}_{slot}"
            booking_info = booked_map.get(key)
            if booking_info:
                is_own = booking_info.get("user_id") == user_id
                day_slots.append({"time": slot, "status": "own" if is_own else "booked"})
            else:
                day_slots.append({"time": slot, "status": "available"})
        calendar.append({"date": d.isoformat(), "weekday": d.weekday(), "slots": day_slots})

    return {"calendar": calendar, "price": BOOKING_PRICE, "advance_percent": BOOKING_ADVANCE_PERCENT}


@router.post("/bookings/book")
async def book_slot(req: BookingRequest, request: Request):
    user = await get_current_user(request)
    user_id = user["_id"]

    try:
        book_date = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    now_utc = datetime.now(timezone.utc)
    today = (now_utc + timedelta(hours=3)).date()

    if book_date < today:
        raise HTTPException(400, "Cannot book in the past")
    if book_date > today + timedelta(days=30):
        raise HTTPException(400, "Cannot book more than 30 days ahead")
    if book_date.weekday() >= 5:
        raise HTTPException(400, "No consultations on weekends")
    if req.time_slot not in BOOKING_SLOTS:
        raise HTTPException(400, f"Invalid time slot. Available: {BOOKING_SLOTS}")

    existing = await db.bookings.find_one({
        "date": req.date,
        "time_slot": req.time_slot,
        "status": {"$in": ["booked", "confirmed"]},
    })
    if existing:
        raise HTTPException(409, "This slot is already booked")

    booking = {
        "user_id": user_id,
        "user_email": user.get("email", ""),
        "date": req.date,
        "time_slot": req.time_slot,
        "price": BOOKING_PRICE,
        "advance_paid": BOOKING_PRICE * BOOKING_ADVANCE_PERCENT / 100,
        "status": "booked",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notification_sent": False,
    }
    result = await db.bookings.insert_one(booking)

    return {
        "booking_id": str(result.inserted_id),
        "date": req.date,
        "time_slot": req.time_slot,
        "advance_amount": booking["advance_paid"],
        "status": "booked",
    }


@router.get("/bookings/my")
async def get_my_bookings(request: Request):
    user = await get_current_user(request)
    bookings = await db.bookings.find(
        {"user_id": user["_id"]},
        {"_id": 0, "date": 1, "time_slot": 1, "status": 1, "price": 1, "advance_paid": 1},
    ).sort("date", 1).to_list(50)
    return {"bookings": bookings}
