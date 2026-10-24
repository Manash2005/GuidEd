import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD
)
from db.mongo import get_database
from models.user_model import UserResponse

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> UserResponse:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        user = await db["users"].find_one({"userId": user_id}, {"_id": 0, "hashedPassword": 0})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query failed ({type(e).__name__}): {str(e)}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Server-side validation of account status: immediately revokes access for suspended accounts
    user_status = user.get("status", "active")
    if user_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user_status}. Please contact support."
        )

    if "role" not in user:
        user["role"] = "student"
    if "status" not in user:
        user["status"] = "active"

    return UserResponse(**user)


def require_role(*allowed_roles: str) -> Callable:
    """
    Role-based authorization dependency factory.
    Verifies that the server-retrieved user role matches one of allowed_roles.
    """
    async def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{current_user.role}' is not authorized for this resource"
            )
        return current_user
    return role_checker


# Role dependencies
require_student = require_role("student")
require_mentor = require_role("mentor")
require_admin = require_role("admin")
require_mentor_or_admin = require_role("mentor", "admin")
require_any_authenticated = get_current_user


async def log_audit_event(
    admin_user: UserResponse,
    action: str,
    target_user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Records an administrative audit log entry to MongoDB without logging sensitive data.
    """
    db = get_database()
    if db is None:
        return

    log_entry = {
        "logId": f"log_{uuid.uuid4().hex[:12]}",
        "adminUserId": admin_user.userId,
        "adminEmail": admin_user.email,
        "action": action,
        "targetUserId": target_user_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc)
    }

    try:
        await db["audit_logs"].insert_one(log_entry)
    except Exception as e:
        print(f"Warning: Failed to persist audit log: {e}")


async def bootstrap_initial_admin():
    """
    Provisions initial admin account on startup if no admin exists.
    Uses INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD from config.
    """
    db = get_database()
    if db is None:
        return

    try:
        admin_count = await db["users"].count_documents({"role": "admin"})
        if admin_count == 0 and INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD:
            existing = await db["users"].find_one({"email": INITIAL_ADMIN_EMAIL.lower()})
            now = datetime.now(timezone.utc)
            if existing:
                await db["users"].update_one(
                    {"email": INITIAL_ADMIN_EMAIL.lower()},
                    {"$set": {"role": "admin", "status": "active", "updatedAt": now}}
                )
                print(f"Promoted existing user {INITIAL_ADMIN_EMAIL} to admin role.")
            else:
                user_id = f"usr_{uuid.uuid4().hex[:12]}"
                admin_doc = {
                    "userId": user_id,
                    "email": INITIAL_ADMIN_EMAIL.lower(),
                    "fullName": "System Administrator",
                    "role": "admin",
                    "status": "active",
                    "hashedPassword": hash_password(INITIAL_ADMIN_PASSWORD),
                    "createdAt": now,
                    "updatedAt": now
                }
                await db["users"].insert_one(admin_doc)
                print(f"Bootstrapped initial admin account: {INITIAL_ADMIN_EMAIL}")
    except Exception as e:
        print(f"Notice: Initial admin bootstrap skipped: {e}")
