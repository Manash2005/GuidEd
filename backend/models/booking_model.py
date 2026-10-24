from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

class CreateBookingRequest(BaseModel):
    mentorId: str = Field(..., description="Mentor ID (e.g. M033)")
    slotStart: datetime = Field(..., description="UTC start time of the session")
    durationMinutes: int = Field(default=30, ge=15, le=120)
    topic: str = Field(..., min_length=5, max_length=500, description="Career topic or discussion goals")

class TimeSlot(BaseModel):
    slotStart: datetime
    slotEnd: datetime
    isAvailable: bool = True

class BookingResponse(BaseModel):
    bookingId: str
    userId: str
    userName: str
    userEmail: str
    mentorId: str
    mentorName: str
    slotStart: datetime
    slotEnd: datetime
    durationMinutes: int
    status: Literal["confirmed", "cancelled", "completed"]
    topic: str
    meetingLink: Optional[str] = None
    calendarEventId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
