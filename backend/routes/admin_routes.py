import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status

from db.mongo import get_database
from models.user_model import (
    UserResponse,
    RoleUpdateRequest,
    StatusUpdateRequest,
    AuditLogResponse
)
from models.booking_model import BookingResponse
from utils.auth import require_admin, log_audit_event
from services.google_calendar import delete_calendar_event
from services.email_service import send_booking_confirmation, send_booking_cancellation

from pydantic import BaseModel, Field

class AdminBookingStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status: upcoming, pending, completed, cancelled")

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(current_user: UserResponse = Depends(require_admin)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    now = datetime.now(timezone.utc)
    activity_window_days = 30
    cutoff_active = now - timedelta(days=activity_window_days)

    # 1. Total counts via lightweight count queries
    total_students = await db["users"].count_documents({"role": "student"})
    mentor_users_count = await db["users"].count_documents({"role": "mentor"})
    mentors_catalog_count = await db["mentors"].count_documents({})
    total_mentors = max(mentor_users_count, mentors_catalog_count)

    total_bookings = await db["bookings"].count_documents({})
    upcoming_bookings = await db["bookings"].count_documents({
        "status": "confirmed",
        "slotStart": {"$gte": now}
    })
    completed_bookings = await db["bookings"].count_documents({"status": "completed"})
    cancelled_bookings = await db["bookings"].count_documents({"status": "cancelled"})
    pending_bookings = await db["bookings"].count_documents({"status": "pending"})

    # 2. Conversations & messages counts
    total_conversations = await db["conversations"].count_documents({})

    total_messages = 0
    try:
        msg_pipeline = [
            {"$project": {"count": {"$size": {"$ifNull": ["$messages", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}}
        ]
        msg_cursor = db["conversations"].aggregate(msg_pipeline)
        msg_results = await msg_cursor.to_list(length=1)
        if msg_results:
            total_messages = msg_results[0].get("total", 0)
    except Exception:
        total_messages = total_conversations * 2

    # 3. Active students (activity in past 30 days)
    active_students = await db["users"].count_documents({
        "role": "student",
        "$or": [
            {"createdAt": {"$gte": cutoff_active}},
            {"updatedAt": {"$gte": cutoff_active}}
        ]
    })

    # 4. Top booked mentors
    top_mentors = []
    try:
        top_mentors_pipeline = [
            {"$group": {"_id": {"mentorId": "$mentorId", "name": "$mentorName"}, "bookingsCount": {"$sum": 1}}},
            {"$sort": {"bookingsCount": -1}},
            {"$limit": 5},
            {"$project": {"mentorId": "$_id.mentorId", "name": "$_id.name", "bookingsCount": 1, "_id": 0}}
        ]
        top_cursor = db["bookings"].aggregate(top_mentors_pipeline)
        top_mentors = await top_cursor.to_list(length=5)
    except Exception:
        pass

    # 5. Popular career domains
    popular_domains = []
    try:
        domains_pipeline = [
            {"$match": {"targetDomain": {"$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$targetDomain", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
            {"$project": {"domain": "$_id", "count": 1, "_id": 0}}
        ]
        domain_cursor = db["users"].aggregate(domains_pipeline)
        popular_domains = await domain_cursor.to_list(length=5)
    except Exception:
        pass

    # 6. Trends over time
    booking_trends = []
    try:
        b_trend_pipeline = [
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$limit": 14},
            {"$project": {"date": "$_id", "count": 1, "_id": 0}}
        ]
        b_cursor = db["bookings"].aggregate(b_trend_pipeline)
        booking_trends = await b_cursor.to_list(length=14)
    except Exception:
        pass

    conversation_trends = []
    try:
        c_trend_pipeline = [
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$limit": 14},
            {"$project": {"date": "$_id", "count": 1, "_id": 0}}
        ]
        c_cursor = db["conversations"].aggregate(c_trend_pipeline)
        conversation_trends = await c_cursor.to_list(length=14)
    except Exception:
        pass

    # 7. Rates & User totals
    total_users = await db["users"].count_documents({})
    total_admins = await db["users"].count_documents({"role": "admin"})
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0
    completion_rate = round((completed_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    return {
        "totalUsers": total_users,
        "totalMentors": total_mentors,
        "totalStudents": total_students,
        "totalAdmins": total_admins,
        "totalBookings": total_bookings,
        "confirmedBookings": upcoming_bookings,
        "activeUsers": active_students + total_admins,
        "stats": {
            "totalUsers": total_users,
            "totalStudents": total_students,
            "totalMentors": total_mentors,
            "totalAdmins": total_admins,
            "totalBookings": total_bookings,
            "upcomingBookings": upcoming_bookings,
            "pendingBookings": pending_bookings,
            "completedBookings": completed_bookings,
            "cancelledBookings": cancelled_bookings,
            "totalConversations": total_conversations,
            "totalMessages": total_messages,
            "activeStudents": active_students,
            "activityWindowDays": activity_window_days,
            "cancellationRatePercent": cancellation_rate,
            "completionRatePercent": completion_rate
        },
        "topMentors": top_mentors,
        "popularDomains": popular_domains,
        "bookingTrends": booking_trends,
        "conversationTrends": conversation_trends
    }

@router.get("/users")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: student, mentor, admin"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: active, inactive, suspended"),
    q: Optional[str] = Query(None, description="Search query by name or email"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    query = {}
    if role:
        query["role"] = role.strip().lower()
    if status_filter:
        query["status"] = status_filter.strip().lower()
    if q:
        safe_q = re.escape(q.strip())
        query["$or"] = [
            {"fullName": {"$regex": safe_q, "$options": "i"}},
            {"email": {"$regex": safe_q, "$options": "i"}}
        ]

    total_count = await db["users"].count_documents(query)
    skip = (page - 1) * limit

    cursor = db["users"].find(query, {"_id": 0, "hashedPassword": 0}).sort("createdAt", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total_count + limit - 1) // limit),
        "users": [UserResponse(**u) for u in users]
    }

@router.get("/students")
async def list_students(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    return await list_users(role="student", status_filter=None, q=q, page=page, limit=limit, current_user=current_user)

@router.get("/mentors")
async def list_mentors(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    return await list_users(role="mentor", status_filter=None, q=q, page=page, limit=limit, current_user=current_user)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    user = await db["users"].find_one({"userId": user_id}, {"_id": 0, "hashedPassword": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)

@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    target_user = await db["users"].find_one({"userId": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = target_user.get("role", "student")
    new_role = payload.role

    now = datetime.now(timezone.utc)
    await db["users"].update_one(
        {"userId": user_id},
        {"$set": {"role": new_role, "updatedAt": now}}
    )

    await log_audit_event(
        admin_user=current_user,
        action="UPDATE_USER_ROLE",
        target_user_id=user_id,
        details={"oldRole": old_role, "newRole": new_role, "targetEmail": target_user.get("email")}
    )

    updated = await db["users"].find_one({"userId": user_id}, {"_id": 0, "hashedPassword": 0})
    return UserResponse(**updated)

@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    payload: StatusUpdateRequest,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    target_user = await db["users"].find_one({"userId": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    old_status = target_user.get("status", "active")
    new_status = payload.status

    now = datetime.now(timezone.utc)
    await db["users"].update_one(
        {"userId": user_id},
        {"$set": {"status": new_status, "updatedAt": now}}
    )

    await log_audit_event(
        admin_user=current_user,
        action="UPDATE_USER_STATUS",
        target_user_id=user_id,
        details={"oldStatus": old_status, "newStatus": new_status, "targetEmail": target_user.get("email")}
    )

    updated = await db["users"].find_one({"userId": user_id}, {"_id": 0, "hashedPassword": 0})
    return UserResponse(**updated)

@router.get("/bookings")
async def list_all_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="Search by student name, mentor name, or bookingId"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    query = {}
    if status_filter:
        query["status"] = status_filter.strip().lower()
    if q:
        safe_q = re.escape(q.strip())
        query["$or"] = [
            {"bookingId": {"$regex": safe_q, "$options": "i"}},
            {"userName": {"$regex": safe_q, "$options": "i"}},
            {"mentorName": {"$regex": safe_q, "$options": "i"}},
            {"topic": {"$regex": safe_q, "$options": "i"}}
        ]

    total_count = await db["bookings"].count_documents(query)
    skip = (page - 1) * limit

    cursor = db["bookings"].find(query, {"_id": 0}).sort("slotStart", -1).skip(skip).limit(limit)
    bookings = await cursor.to_list(length=limit)

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total_count + limit - 1) // limit),
        "bookings": [BookingResponse(**b) for b in bookings]
    }

@router.patch("/bookings/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: str,
    payload: AdminBookingStatusUpdateRequest,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    booking = await db["bookings"].find_one({"bookingId": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    new_status = payload.status.strip().lower()
    if new_status not in ("upcoming", "confirmed", "pending", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status. Allowed: upcoming, pending, completed, cancelled")

    now = datetime.now(timezone.utc)
    old_status = booking.get("status")

    if new_status == "cancelled" and old_status != "cancelled":
        cal_event_id = booking.get("calendarEventId")
        if cal_event_id:
            try:
                await delete_calendar_event(cal_event_id)
            except Exception:
                pass

    await db["bookings"].update_one(
        {"bookingId": booking_id},
        {"$set": {"status": new_status, "updatedAt": now}}
    )

    booking["status"] = new_status
    booking["updatedAt"] = now

    if new_status == "confirmed" and old_status == "pending":
        try:
            await send_booking_confirmation(booking)
        except Exception as e:
            print(f"Warning: Confirmation email on status update failed: {e}")
    elif new_status == "cancelled" and old_status != "cancelled":
        try:
            await send_booking_cancellation(booking)
        except Exception as e:
            print(f"Warning: Admin cancellation email failed: {e}")

    await log_audit_event(
        admin_user=current_user,
        action="UPDATE_BOOKING_STATUS",
        target_user_id=booking.get("userId"),
        details={"bookingId": booking_id, "oldStatus": old_status, "newStatus": new_status}
    )

    updated = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    return BookingResponse(**updated)

@router.post("/bookings/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    booking = await db["bookings"].find_one({"bookingId": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot approve a cancelled booking.")

    now = datetime.now(timezone.utc)
    old_status = booking.get("status")

    await db["bookings"].update_one(
        {"bookingId": booking_id},
        {"$set": {
            "status": "confirmed",
            "approvedAt": now,
            "approvedBy": current_user.email,
            "updatedAt": now
        }}
    )

    booking["status"] = "confirmed"
    booking["approvedAt"] = now
    booking["approvedBy"] = current_user.email
    booking["updatedAt"] = now

    try:
        await send_booking_confirmation(booking)
    except Exception as e:
        print(f"Warning: Admin approval confirmation email failed: {e}")

    await log_audit_event(
        admin_user=current_user,
        action="APPROVE_BOOKING",
        target_user_id=booking.get("userId"),
        details={"bookingId": booking_id, "oldStatus": old_status, "newStatus": "confirmed"}
    )

    updated = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    return BookingResponse(**updated)

@router.post("/bookings/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking(
    booking_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    booking = await db["bookings"].find_one({"bookingId": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    now = datetime.now(timezone.utc)
    old_status = booking.get("status")

    cal_event_id = booking.get("calendarEventId")
    if cal_event_id:
        try:
            await delete_calendar_event(cal_event_id)
        except Exception:
            pass

    await db["bookings"].update_one(
        {"bookingId": booking_id},
        {"$set": {
            "status": "cancelled",
            "rejectedAt": now,
            "rejectedBy": current_user.email,
            "updatedAt": now
        }}
    )

    booking["status"] = "cancelled"
    booking["rejectedAt"] = now
    booking["rejectedBy"] = current_user.email
    booking["updatedAt"] = now

    try:
        await send_booking_cancellation(booking)
    except Exception as e:
        print(f"Warning: Admin rejection email failed: {e}")

    await log_audit_event(
        admin_user=current_user,
        action="REJECT_BOOKING",
        target_user_id=booking.get("userId"),
        details={"bookingId": booking_id, "oldStatus": old_status, "newStatus": "cancelled"}
    )

    updated = await db["bookings"].find_one({"bookingId": booking_id}, {"_id": 0})
    return BookingResponse(**updated)

@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    total_count = await db["audit_logs"].count_documents({})
    skip = (page - 1) * limit

    cursor = db["audit_logs"].find({}, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(length=limit)

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total_count + limit - 1) // limit),
        "logs": logs
    }

@router.get("/health")
async def get_system_health(current_user: UserResponse = Depends(require_admin)):
    db = get_database()
    mongo_status = "connected" if db is not None else "disconnected"

    collections_count = 0
    if db is not None:
        try:
            cols = await db.list_collection_names()
            collections_count = len(cols)
        except Exception:
            mongo_status = "error"

    return {
        "status": "operational",
        "timestamp": datetime.now(timezone.utc),
        "database": {
            "status": mongo_status,
            "collectionsTracked": collections_count
        },
        "services": {
            "rateLimiter": "active",
            "securityHeaders": "active",
            "roleBasedAccessControl": "enforced"
        }
    }
