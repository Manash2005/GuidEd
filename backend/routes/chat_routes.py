import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status

from db.mongo import get_database
from models.user_model import UserResponse
from models.chat_model import (
    ChatMessage,
    CreateConversationRequest,
    SendMessageRequest,
    ConversationSummaryResponse,
    ConversationDetailResponse
)
from utils.auth import get_current_user
from agent.guardrails import validate_query
from agent.recommender import recommend

router = APIRouter(prefix="/chat", tags=["Chat Conversations"])

def _now() -> datetime:
    return datetime.now(timezone.utc)

@router.post("/conversations", response_model=ConversationDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: CreateConversationRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = _now()
    title = payload.title or (payload.initialMessage[:40] if payload.initialMessage else "New Career Conversation")
    messages = []

    if payload.initialMessage:
        user_msg = ChatMessage(
            messageId=f"msg_{uuid.uuid4().hex[:10]}",
            role="user",
            content=payload.initialMessage.strip(),
            recommendations=[],
            createdAt=now
        )
        messages.append(user_msg)

        guard = validate_query(payload.initialMessage)
        if not guard.is_allowed:
            asst_msg = ChatMessage(
                messageId=f"msg_{uuid.uuid4().hex[:10]}",
                role="assistant",
                content=guard.reason or "GuidEd only supports career and mentorship inquiries.",
                recommendations=[],
                createdAt=_now()
            )
        else:
            rec = recommend(payload.initialMessage)
            asst_msg = ChatMessage(
                messageId=f"msg_{uuid.uuid4().hex[:10]}",
                role="assistant",
                content=rec["summary"],
                recommendations=rec["recommendations"],
                createdAt=_now()
            )
        messages.append(asst_msg)

    doc = {
        "conversationId": conversation_id,
        "userId": current_user.userId,
        "title": title,
        "messages": [m.model_dump(mode="json") for m in messages],
        "createdAt": now,
        "updatedAt": now
    }

    await db["conversations"].insert_one(doc)

    return ConversationDetailResponse(
        conversationId=conversation_id,
        userId=current_user.userId,
        title=title,
        messages=messages,
        createdAt=now,
        updatedAt=now
    )

@router.get("/conversations", response_model=List[ConversationSummaryResponse])
async def list_conversations(current_user: UserResponse = Depends(get_current_user)):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    cursor = db["conversations"].find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("updatedAt", -1)

    items = await cursor.to_list(length=100)
    summaries = []
    for item in items:
        summaries.append(ConversationSummaryResponse(
            conversationId=item["conversationId"],
            userId=item["userId"],
            title=item.get("title", "Career Conversation"),
            messageCount=len(item.get("messages", [])),
            createdAt=item["createdAt"],
            updatedAt=item["updatedAt"]
        ))
    return summaries

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    conv = await db["conversations"].find_one({"conversationId": conversation_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.get("userId") != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied to this conversation")

    return ConversationDetailResponse(
        conversationId=conv["conversationId"],
        userId=conv["userId"],
        title=conv.get("title", "Career Conversation"),
        messages=[ChatMessage(**m) for m in conv.get("messages", [])],
        createdAt=conv["createdAt"],
        updatedAt=conv["updatedAt"]
    )

@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessage)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    conv = await db["conversations"].find_one({"conversationId": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.get("userId") != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied to this conversation")

    now = _now()
    user_msg = ChatMessage(
        messageId=f"msg_{uuid.uuid4().hex[:10]}",
        role="user",
        content=payload.message.strip(),
        recommendations=[],
        createdAt=now
    )

    guard = validate_query(payload.message)
    if not guard.is_allowed:
        asst_msg = ChatMessage(
            messageId=f"msg_{uuid.uuid4().hex[:10]}",
            role="assistant",
            content=guard.reason or "GuidEd only supports career and mentorship inquiries.",
            recommendations=[],
            createdAt=_now()
        )
    else:
        rec = recommend(payload.message, constraints=payload.constraints)
        asst_msg = ChatMessage(
            messageId=f"msg_{uuid.uuid4().hex[:10]}",
            role="assistant",
            content=rec["summary"],
            recommendations=rec["recommendations"],
            createdAt=_now()
        )

    await db["conversations"].update_one(
        {"conversationId": conversation_id},
        {
            "$push": {
                "messages": {
                    "$each": [
                        user_msg.model_dump(mode="json"),
                        asst_msg.model_dump(mode="json")
                    ]
                }
            },
            "$set": {"updatedAt": _now()}
        }
    )

    return asst_msg

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    conv = await db["conversations"].find_one({"conversationId": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.get("userId") != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied to this conversation")

    await db["conversations"].delete_one({"conversationId": conversation_id})
    return {"deleted": True, "conversationId": conversation_id}
