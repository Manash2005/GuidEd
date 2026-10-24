import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends

from db.mongo import get_database
from models.user_model import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserProfileUpdate
)
from utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    # Security check: Ensure public registration can never assign admin role
    assigned_role = payload.role or "student"
    if assigned_role not in ("student", "mentor"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified. Public registration only allows 'student' or 'mentor'."
        )

    normalized_email = payload.email.strip().lower()

    try:
        existing_user = await db["users"].find_one({"email": normalized_email})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query failed ({type(e).__name__}): {str(e)}"
        )

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
        "role": assigned_role,
        "status": "active",
        "mentorId": payload.mentorId.strip().upper() if payload.mentorId else None,
        "targetDomain": payload.targetDomain.strip() if payload.targetDomain else None,
        "educationLevel": payload.educationLevel.strip() if payload.educationLevel else None,
        "hashedPassword": hashed_pwd,
        "createdAt": created_at,
        "updatedAt": created_at
    }

    try:
        await db["users"].insert_one(user_doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database write failed ({type(e).__name__}): {str(e)}"
        )

    return UserResponse(
        userId=user_id,
        email=normalized_email,
        fullName=payload.fullName.strip(),
        role=assigned_role,
        status="active",
        mentorId=user_doc["mentorId"],
        targetDomain=user_doc["targetDomain"],
        educationLevel=user_doc["educationLevel"],
        createdAt=created_at,
        updatedAt=created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    ident = payload.email.strip()
    if "@" in ident:
        query = {"email": ident.lower()}
    else:
        query = {
            "$or": [
                {"mentorId": ident.upper()},
                {"userId": ident},
                {"email": ident.lower()}
            ]
        }
    try:
        user = await db["users"].find_one(query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query failed ({type(e).__name__}): {str(e)}"
        )

    if not user or not verify_password(payload.password, user.get("hashedPassword", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_status = user.get("status", "active")
    if user_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user_status}. Please contact support."
        )

    user_role = user.get("role", "student")

    user_response = UserResponse(
        userId=user["userId"],
        email=user["email"],
        fullName=user["fullName"],
        role=user_role,
        status=user_status,
        mentorId=user.get("mentorId"),
        targetDomain=user.get("targetDomain"),
        educationLevel=user.get("educationLevel"),
        createdAt=user["createdAt"],
        updatedAt=user.get("updatedAt")
    )

    token = create_access_token({
        "sub": user["userId"],
        "email": user["email"],
        "role": user_role
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response
    )

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    updates = {}
    if payload.email is not None and str(payload.email).strip():
        new_email = str(payload.email).strip().lower()
        dup = await db["users"].find_one({"email": new_email, "userId": {"$ne": current_user.userId}})
        if dup:
            raise HTTPException(status_code=409, detail="Email is already registered by another account")
        updates["email"] = new_email
        if current_user.mentorId:
            await db["mentors"].update_one(
                {"mentorId": current_user.mentorId.upper()},
                {"$set": {"email": new_email}}
            )

    if payload.fullName is not None:
        updates["fullName"] = payload.fullName.strip()
    if payload.targetDomain is not None:
        updates["targetDomain"] = payload.targetDomain.strip()
    if payload.educationLevel is not None:
        updates["educationLevel"] = payload.educationLevel.strip()

    updates["updatedAt"] = datetime.now(timezone.utc)

    await db["users"].update_one(
        {"userId": current_user.userId},
        {"$set": updates}
    )

    updated_user = await db["users"].find_one({"userId": current_user.userId}, {"_id": 0, "hashedPassword": 0})
    return UserResponse(**updated_user)
