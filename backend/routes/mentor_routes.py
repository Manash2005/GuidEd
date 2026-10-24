from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query, status

from db.mongo import get_database
from models.user_model import UserResponse
from models.booking_model import BookingResponse
from utils.auth import require_mentor

router = APIRouter(prefix="/mentor", tags=["Mentor"])

class MentorStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New booking status ('confirmed' or 'completed')")

class MentorProfileUpdateRequest(BaseModel):
    email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    domain: Optional[str] = None
    city: Optional[str] = None
    seniority: Optional[str] = None
    sectorsOfExpertise: Optional[List[str]] = None
    rolesOfExpertise: Optional[List[str]] = None

def _resolve_mentor_id(current_user: UserResponse) -> str:
    if current_user.mentorId:
        return current_user.mentorId.strip().upper()
    # Fallback to deterministic pseudo-id for newly registered mentors without explicit link
    return f"M_{current_user.userId.replace('usr_', '')[:6].upper()}"

@router.get("/dashboard")
async def get_mentor_dashboard(current_user: UserResponse = Depends(require_mentor)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    now = datetime.now(timezone.utc)

    # Fetch mentor profile details if available
    mentor_profile = await db["mentors"].find_one(
        {"mentorId": mentor_id},
        {"_id": 0}
    )

    # Aggregated session stats
    total_sessions = await db["bookings"].count_documents({"mentorId": mentor_id})
    upcoming_sessions = await db["bookings"].count_documents({
        "mentorId": mentor_id,
        "status": "confirmed",
        "slotStart": {"$gte": now}
    })
    completed_sessions = await db["bookings"].count_documents({
        "mentorId": mentor_id,
        "status": "completed"
    })

    # Next upcoming session
    next_session = await db["bookings"].find_one(
        {"mentorId": mentor_id, "status": "confirmed", "slotStart": {"$gte": now}},
        {"_id": 0},
        sort=[("slotStart", 1)]
    )

    # Recent 5 bookings
    recent_bookings_cursor = db["bookings"].find(
        {"mentorId": mentor_id},
        {"_id": 0}
    ).sort("slotStart", -1).limit(5)
    recent_bookings = await recent_bookings_cursor.to_list(length=5)

    return {
        "mentorId": mentor_id,
        "profile": mentor_profile or {
            "name": current_user.fullName,
            "email": current_user.email,
            "domain": current_user.targetDomain or "Career Guidance"
        },
        "stats": {
            "totalSessions": total_sessions,
            "upcomingSessions": upcoming_sessions,
            "completedSessions": completed_sessions,
            "rating": mentor_profile.get("rating", 5.0) if mentor_profile else 5.0
        },
        "nextSession": next_session,
        "recentBookings": recent_bookings
    }

@router.get("/bookings", response_model=List[BookingResponse])
async def list_mentor_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserResponse = Depends(require_mentor)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    query = {"mentorId": mentor_id}
    if status_filter:
        query["status"] = status_filter.strip().lower()

    cursor = db["bookings"].find(query, {"_id": 0}).sort("slotStart", 1)
    bookings = await cursor.to_list(length=100)
    return [BookingResponse(**b) for b in bookings]

@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_mentor_booking_detail(
    booking_id: str,
    current_user: UserResponse = Depends(require_mentor)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    booking = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Resource-level authorization: ensure this booking belongs to this mentor
    if booking.get("mentorId") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied: booking belongs to another mentor")

    return BookingResponse(**booking)

@router.get("/bookings/{booking_id}/student-context")
async def get_booking_student_context(
    booking_id: str,
    current_user: UserResponse = Depends(require_mentor)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    booking = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.get("mentorId") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied: booking belongs to another mentor")

    student_id = booking.get("userId")
    student = await db["users"].find_one(
        {"userId": student_id},
        {"_id": 0, "hashedPassword": 0}
    )

    # Privacy constraint: Only return context strictly associated with this session
    return {
        "bookingId": booking_id,
        "topic": booking.get("topic", "General Career Advice"),
        "scheduledTime": booking.get("slotStart"),
        "durationMinutes": booking.get("durationMinutes", 30),
        "meetingLink": booking.get("meetingLink"),
        "student": {
            "name": booking.get("userName"),
            "targetDomain": student.get("targetDomain") if student else None,
            "educationLevel": student.get("educationLevel") if student else None
        },
        "sessionContext": {
            "discussionGoal": booking.get("topic"),
            "sessionStatus": booking.get("status")
        }
    }

@router.patch("/bookings/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: str,
    payload: MentorStatusUpdateRequest,
    current_user: UserResponse = Depends(require_mentor)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    booking = await db["bookings"].find_one({"bookingId": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.get("mentorId") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied: booking belongs to another mentor")

    new_status = payload.status.strip().lower()
    if new_status not in ("confirmed", "completed"):
        raise HTTPException(status_code=400, detail="Mentors can only set status to 'confirmed' or 'completed'")

    now = datetime.now(timezone.utc)
    await db["bookings"].update_one(
        {"bookingId": booking_id},
        {"$set": {"status": new_status, "updatedAt": now}}
    )
    booking["status"] = new_status
    booking["updatedAt"] = now
    booking.pop("_id", None)
    return BookingResponse(**booking)

@router.get("/profile")
async def get_mentor_profile(current_user: UserResponse = Depends(require_mentor)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    profile = await db["mentors"].find_one({"mentorId": mentor_id}, {"_id": 0})
    if not profile:
        return {
            "mentorId": mentor_id,
            "name": current_user.fullName,
            "email": current_user.email,
            "domain": current_user.targetDomain or "Career Guidance",
            "company": "Independent Mentor"
        }
    return profile

@router.put("/profile")
async def update_mentor_profile(
    payload: MentorProfileUpdateRequest,
    current_user: UserResponse = Depends(require_mentor)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    mentor_id = _resolve_mentor_id(current_user)
    updates = {}
    if payload.email is not None and payload.email.strip():
        new_email = payload.email.strip().lower()
        dup = await db["users"].find_one({"email": new_email, "userId": {"$ne": current_user.userId}})
        if dup:
            raise HTTPException(status_code=409, detail="Email is already registered by another account")
        updates["email"] = new_email
        await db["users"].update_one(
            {"userId": current_user.userId},
            {"$set": {"email": new_email, "updatedAt": datetime.now(timezone.utc)}}
        )

    if payload.company is not None:
        updates["company"] = payload.company.strip()
    if payload.role is not None:
        updates["role"] = payload.role.strip()
    if payload.domain is not None:
        updates["domain"] = payload.domain.strip()
    if payload.city is not None:
        updates["city"] = payload.city.strip()
    if payload.seniority is not None:
        updates["seniority"] = payload.seniority.strip()
    if payload.sectorsOfExpertise is not None:
        updates["sectorsOfExpertise"] = payload.sectorsOfExpertise
    if payload.rolesOfExpertise is not None:
        updates["rolesOfExpertise"] = payload.rolesOfExpertise

    await db["mentors"].update_one(
        {"mentorId": mentor_id},
        {"$set": updates},
        upsert=True
    )
    profile = await db["mentors"].find_one({"mentorId": mentor_id}, {"_id": 0})
    return profile
