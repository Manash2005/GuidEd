from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status

from db.mongo import get_database
from models.user_model import UserResponse
from models.booking_model import BookingResponse
from models.chat_model import ConversationSummaryResponse
from utils.auth import require_student

router = APIRouter(prefix="/student", tags=["Student"])

@router.get("/dashboard")
async def get_student_dashboard(current_user: UserResponse = Depends(require_student)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    now = datetime.now(timezone.utc)

    # 1. Booking counts
    total_bookings = await db["bookings"].count_documents({"userId": current_user.userId})
    upcoming_bookings_count = await db["bookings"].count_documents({
        "userId": current_user.userId,
        "status": "confirmed",
        "slotStart": {"$gte": now}
    })
    completed_bookings_count = await db["bookings"].count_documents({
        "userId": current_user.userId,
        "status": "completed"
    })

    # 2. Upcoming bookings list
    upcoming_cursor = db["bookings"].find(
        {"userId": current_user.userId, "status": "confirmed", "slotStart": {"$gte": now}},
        {"_id": 0}
    ).sort("slotStart", 1).limit(5)
    upcoming_bookings = await upcoming_cursor.to_list(length=5)

    # 3. Recent conversations
    conv_cursor = db["conversations"].find(
        {"userId": current_user.userId},
        {"_id": 0, "messages": {"$slice": -1}}
    ).sort("updatedAt", -1).limit(5)
    recent_convs = await conv_cursor.to_list(length=5)
    total_conversations = await db["conversations"].count_documents({"userId": current_user.userId})

    return {
        "user": current_user,
        "stats": {
            "totalBookings": total_bookings,
            "upcomingBookings": upcoming_bookings_count,
            "completedBookings": completed_bookings_count,
            "totalConversations": total_conversations
        },
        "upcomingBookings": upcoming_bookings,
        "recentConversations": [
            {
                "conversationId": c["conversationId"],
                "title": c.get("title", "Career Discussion"),
                "createdAt": c.get("createdAt"),
                "updatedAt": c.get("updatedAt"),
                "messageCount": c.get("messageCount", len(c.get("messages", []))),
                "lastMessage": c["messages"][0]["content"] if c.get("messages") else None
            }
            for c in recent_convs
        ]
    }

@router.get("/bookings", response_model=List[BookingResponse])
async def list_student_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserResponse = Depends(require_student)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    query = {"userId": current_user.userId}
    if status_filter:
        query["status"] = status_filter.strip().lower()

    cursor = db["bookings"].find(query, {"_id": 0}).sort("slotStart", -1)
    bookings = await cursor.to_list(length=100)
    return [BookingResponse(**b) for b in bookings]

@router.get("/conversations", response_model=List[ConversationSummaryResponse])
async def list_student_conversations(current_user: UserResponse = Depends(require_student)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    cursor = db["conversations"].find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("updatedAt", -1)
    convs = await cursor.to_list(length=100)
    summaries = []
    for c in convs:
        count = c.get("messageCount")
        if count is None:
            count = len(c.get("messages", []))
        summaries.append(ConversationSummaryResponse(
            conversationId=c["conversationId"],
            userId=c["userId"],
            title=c.get("title", "Career Guidance"),
            messageCount=count,
            createdAt=c["createdAt"],
            updatedAt=c["updatedAt"]
        ))
    return summaries
