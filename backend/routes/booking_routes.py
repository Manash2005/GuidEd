import os
import uuid
import json
from pathlib import Path
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status

from db.mongo import get_database
from models.user_model import UserResponse
from models.booking_model import (
    TimeSlot,
    CreateBookingRequest,
    BookingResponse,
    BookingListResponse
)
from utils.auth import get_current_user
from services.google_calendar import create_calendar_event, delete_calendar_event
from services.email_service import send_booking_confirmation, send_booking_cancellation

router = APIRouter(prefix="/bookings", tags=["Bookings & Scheduling"])

MENTORS_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "mentors.json"

def _load_mentor_name_fallback(mentor_id: str) -> Optional[str]:
    try:
        if MENTORS_DATA_FILE.exists():
            with open(MENTORS_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for m in data:
                    if m.get("mentorId", "").strip().upper() == mentor_id.strip().upper():
                        return m.get("name")
    except Exception:
        pass
    return None

def _now() -> datetime:
    return datetime.now(timezone.utc)

@router.get("/mentors/{mentor_id}/slots", response_model=List[TimeSlot])
async def get_mentor_available_slots(
    mentor_id: str,
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    duration_minutes: int = Query(30, ge=15, le=120)
):
    try:
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    clean_mentor_id = mentor_id.strip().upper()

    # Generate daily potential slots from 09:00 to 17:00 UTC
    day_start = datetime.combine(parsed_date, time(9, 0), tzinfo=timezone.utc)
    day_end = datetime.combine(parsed_date, time(17, 0), tzinfo=timezone.utc)

    # Fetch existing active bookings for this mentor on target date
    cursor = db["bookings"].find({
        "mentorId": clean_mentor_id,
        "slotStart": {"$lt": day_end},
        "slotEnd": {"$gt": day_start}
    })
    existing_all = await cursor.to_list(length=100)
    existing_bookings = [b for b in existing_all if b.get("status") in ("confirmed", "pending")]

    slots = []
    current_start = day_start
    slot_delta = timedelta(minutes=duration_minutes)

    while current_start + slot_delta <= day_end:
        current_end = current_start + slot_delta

        # Check overlap: existing.slotStart < current_end and existing.slotEnd > current_start
        has_conflict = any(
            b["slotStart"] < current_end and b["slotEnd"] > current_start
            for b in existing_bookings
        )

        slots.append(TimeSlot(
            slotStart=current_start,
            slotEnd=current_end,
            isAvailable=not has_conflict
        ))
        current_start += slot_delta

    return slots

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: CreateBookingRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    now = _now()
    slot_start = payload.slotStart
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)

    if slot_start <= now:
        raise HTTPException(status_code=400, detail="Cannot book a time slot in the past.")

    slot_end = slot_start + timedelta(minutes=payload.durationMinutes)
    clean_mentor_id = payload.mentorId.strip().upper()

    # Verify mentor exists
    mentor_doc = await db["mentors"].find_one({"mentorId": clean_mentor_id})
    if mentor_doc:
        mentor_name = mentor_doc.get("name", f"Mentor {clean_mentor_id}")
    else:
        fallback_name = _load_mentor_name_fallback(clean_mentor_id)
        if fallback_name:
            mentor_name = fallback_name
        else:
            raise HTTPException(status_code=404, detail=f"Mentor {clean_mentor_id} not found")

    # Double-booking check 1: Mentor concurrency overlap (confirmed or pending)
    mentor_conflict = await db["bookings"].find_one({
        "mentorId": clean_mentor_id,
        "slotStart": {"$lt": slot_end},
        "slotEnd": {"$gt": slot_start}
    })
    if mentor_conflict and mentor_conflict.get("status") in ("confirmed", "pending"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This mentor already has an active or pending booking for the selected time slot. Please choose another slot."
        )

    # Double-booking check 2: Student schedule overlap (confirmed or pending)
    student_conflict = await db["bookings"].find_one({
        "userId": current_user.userId,
        "slotStart": {"$lt": slot_end},
        "slotEnd": {"$gt": slot_start}
    })
    if student_conflict and student_conflict.get("status") in ("confirmed", "pending"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active mentorship booking overlapping with this time slot."
        )

    booking_id = f"bk_{uuid.uuid4().hex[:12]}"

    mentor_user = await db["users"].find_one({"mentorId": clean_mentor_id})
    mentor_email = mentor_user.get("email") if mentor_user else None
    if not mentor_email:
        mentor_doc = await db["mentors"].find_one({"mentorId": clean_mentor_id})
        mentor_email = mentor_doc.get("email") if mentor_doc else None

    # Step A: Create Google Calendar & Meet link
    cal_event = await create_calendar_event(
        booking_id=booking_id,
        mentor_id=clean_mentor_id,
        mentor_name=mentor_name,
        student_name=current_user.fullName,
        student_email=current_user.email,
        slot_start=slot_start,
        slot_end=slot_end,
        topic=payload.topic.strip()
    )

    # Step B: Insert booking with initial 'pending' status awaiting admin approval
    booking_doc = {
        "bookingId": booking_id,
        "userId": current_user.userId,
        "userName": current_user.fullName,
        "userEmail": current_user.email,
        "mentorId": clean_mentor_id,
        "mentorName": mentor_name,
        "mentorEmail": mentor_email,
        "slotStart": slot_start,
        "slotEnd": slot_end,
        "durationMinutes": payload.durationMinutes,
        "status": "pending",
        "topic": payload.topic.strip(),
        "meetingLink": cal_event.get("meetingLink"),
        "calendarEventId": cal_event.get("calendarEventId"),
        "createdAt": now,
        "updatedAt": now
    }
    await db["bookings"].insert_one(booking_doc)

    return BookingResponse(**booking_doc)

@router.get("", response_model=List[BookingResponse])
async def list_my_bookings(current_user: UserResponse = Depends(get_current_user)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    cursor = db["bookings"].find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("slotStart", 1)

    bookings = await cursor.to_list(length=100)
    return [BookingResponse(**b) for b in bookings]

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    booking = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    is_owner = booking["userId"] == current_user.userId
    is_mentor = current_user.role == "mentor" and current_user.mentorId == booking["mentorId"]
    is_admin = current_user.role == "admin"
    if not (is_owner or is_mentor or is_admin):
        raise HTTPException(status_code=403, detail="Access denied to this booking")

    return BookingResponse(**booking)

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    booking = await db["bookings"].find_one({"bookingId": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    is_owner = booking["userId"] == current_user.userId
    is_admin = current_user.role == "admin"
    is_mentor = current_user.role == "mentor" and current_user.mentorId == booking.get("mentorId")
    if not (is_owner or is_admin or is_mentor):
        raise HTTPException(status_code=403, detail="Access denied to this booking")

    if booking.get("status") == "cancelled":
        return BookingResponse(**booking)

    cal_event_id = booking.get("calendarEventId")
    if cal_event_id:
        try:
            await delete_calendar_event(cal_event_id)
        except Exception:
            pass

    now = _now()
    await db["bookings"].update_one(
        {"bookingId": booking_id},
        {"$set": {"status": "cancelled", "updatedAt": now}}
    )
    booking["status"] = "cancelled"
    booking["updatedAt"] = now

    try:
        await send_booking_cancellation(booking)
    except Exception as e:
        print(f"Warning: Cancellation email notification error: {e}")

    return BookingResponse(**booking)
