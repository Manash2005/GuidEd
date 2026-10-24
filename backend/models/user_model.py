from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, EmailStr, Field

RoleType = Literal["student", "mentor", "admin"]
StatusType = Literal["active", "inactive", "suspended"]

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    fullName: str = Field(..., min_length=2, max_length=100)
    role: Optional[Literal["student", "mentor"]] = Field(
        default="student",
        description="Public registration can only create a student or mentor account"
    )
    mentorId: Optional[str] = Field(
        default=None,
        description="Optional mentor ID to link if registering as a mentor"
    )
    targetDomain: Optional[str] = None
    educationLevel: Optional[str] = None

class UserLogin(BaseModel):
    email: str = Field(..., min_length=2, description="Email address or Mentor ID (e.g. M001)")
    password: str

class UserResponse(BaseModel):
    userId: str
    email: str
    fullName: str
    role: RoleType = "student"
    status: StatusType = "active"
    mentorId: Optional[str] = None
    targetDomain: Optional[str] = None
    educationLevel: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    fullName: Optional[str] = Field(None, min_length=2, max_length=100)
    targetDomain: Optional[str] = None
    educationLevel: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserInDB(BaseModel):
    userId: str
    email: str
    fullName: str
    hashedPassword: str
    role: RoleType = "student"
    status: StatusType = "active"
    mentorId: Optional[str] = None
    targetDomain: Optional[str] = None
    educationLevel: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None

class RoleUpdateRequest(BaseModel):
    role: RoleType

class StatusUpdateRequest(BaseModel):
    status: StatusType

class AuditLogResponse(BaseModel):
    logId: str
    adminUserId: str
    adminEmail: Optional[str] = None
    action: str
    targetUserId: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
