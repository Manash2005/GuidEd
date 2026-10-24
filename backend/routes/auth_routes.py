import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends

from db.mongo import get_database
from models.user_model import UserRegister, UserLogin, UserResponse, TokenResponse
from utils.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    normalized_email = payload.email.strip().lower()

    existing_user = await db["users"].find_one({"email": normalized_email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    hashed_pwd = hash_password(payload.password)

    user_doc = {
        "userId": user_id,
        "email": normalized_email,
        "fullName": payload.fullName.strip(),
        "hashedPassword": hashed_pwd,
        "createdAt": created_at
    }

    await db["users"].insert_one(user_doc)

    return UserResponse(
        userId=user_id,
        email=normalized_email,
        fullName=payload.fullName.strip(),
        createdAt=created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    normalized_email = payload.email.strip().lower()
    user = await db["users"].find_one({"email": normalized_email})

    if not user or not verify_password(payload.password, user.get("hashedPassword", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_response = UserResponse(
        userId=user["userId"],
        email=user["email"],
        fullName=user["fullName"],
        createdAt=user["createdAt"]
    )

    token = create_access_token({"sub": user["userId"], "email": user["email"]})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response
    )

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
