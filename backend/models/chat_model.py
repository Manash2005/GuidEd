from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

from routes.agent_routes import RecommendationItem

class ChatMessage(BaseModel):
    messageId: str
    role: Literal["user", "assistant", "system"]
    content: str
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    createdAt: datetime

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    initialMessage: Optional[str] = Field(None, max_length=1000)

class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    constraints: Optional[Dict[str, Any]] = None

class UpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)

class ConversationSummaryResponse(BaseModel):
    conversationId: str
    userId: str
    title: str
    messageCount: int = Field(default=0)
    createdAt: datetime
    updatedAt: datetime

class ConversationDetailResponse(BaseModel):
    conversationId: str
    userId: str
    title: str
    messages: List[ChatMessage]
    createdAt: datetime
    updatedAt: datetime
