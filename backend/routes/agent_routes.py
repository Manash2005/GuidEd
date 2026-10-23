from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.recommender import recommend, MentorRecommendation

router = APIRouter(prefix="/agent", tags=["AI Agent & Recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(
        ...,
        description="Student's query or career question (e.g. 'I want mentorship in AI product management')"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional hard constraints, e.g. {'seniority': 'Senior', 'city': 'Bengaluru'}"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of candidate mentors to retrieve from ChromaDB"
    )


class RecommendationItem(BaseModel):
    mentorId: str = Field(..., description="Unique mentor ID (e.g. M033)")
    name: str = Field(..., description="Mentor's verified name")
    matchReason: str = Field(..., description="Why this mentor fits the student's goal")
    relevantExperience: str = Field(..., description="Direct evidence from the mentor's profile")
    limitations: str = Field(..., description="Missing or uncertain details (e.g. missing seniority, unlisted tools)")
    distance: Optional[float] = Field(None, description="Vector similarity distance score")


class RecommendResponse(BaseModel):
    question: str
    hasMatches: bool
    summary: str
    recommendations: List[RecommendationItem]
    candidatesConsidered: int


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_mentors(payload: RecommendRequest):
    """
    Structured AI Mentor Recommendations:
    1. ChromaDB retrieves top candidate mentors by semantic similarity.
    2. Applies any hard constraints (seniority, city, domain, tools).
    3. Sends candidate profiles + query to LLM for grounded reasoning.
    4. Validates mentor IDs against retrieved candidates to prevent hallucination.
    5. Returns structured recommendations with reasons, evidence, and limitations.
    """
    try:
        result = recommend(
            question=payload.query,
            constraints=payload.constraints,
            top_k=payload.top_k
        )
        return RecommendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")
