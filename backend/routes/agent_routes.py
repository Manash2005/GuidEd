from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.recommender import recommend, MentorRecommendation
from agent.guardrails import validate_query

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


class ScoreBreakdown(BaseModel):
    semanticScore: float = Field(..., description="Dense semantic and cross-encoder score [0-1]")
    domainSectorScore: float = Field(..., description="Domain and sector relevance score [0-1]")
    roleToolScore: float = Field(..., description="Role and tool match score [0-1]")
    seniorityQualityScore: float = Field(..., description="Seniority and mentorship quality score [0-1]")


class RecommendationItem(BaseModel):
    mentorId: str = Field(..., description="Unique mentor ID (e.g. M033)")
    name: str = Field(..., description="Mentor's verified name")
    company: Optional[str] = Field(None, description="Company or organization")
    seniority: Optional[str] = Field(None, description="Seniority level (Senior, Mid-Career, etc.)")
    domain: Optional[str] = Field(None, description="Primary domain")
    city: Optional[str] = Field(None, description="City location")
    sectorsOfExpertise: Optional[List[str]] = Field(default_factory=list, description="Sectors of expertise")
    rolesOfExpertise: Optional[List[str]] = Field(default_factory=list, description="Roles of expertise")
    matchReason: str = Field(..., description="Why this mentor fits the student's goal")
    relevantExperience: str = Field(..., description="Direct evidence from the mentor's profile")
    limitations: str = Field(..., description="Missing or uncertain details (e.g. missing seniority, unlisted tools)")
    compositeScore: Optional[float] = Field(None, description="Explainable composite match score [0-1]")
    matchPercentage: Optional[int] = Field(None, description="Match percentage score [0-100]")
    scoreBreakdown: Optional[ScoreBreakdown] = Field(None, description="Breakdown of composite score components")
    distance: Optional[float] = Field(None, description="Vector similarity distance score")
    rerankScore: Optional[float] = Field(None, description="FlashRank cross-encoder score")


class RecommendResponse(BaseModel):
    question: str
    hasMatches: bool
    summary: str
    recommendations: List[RecommendationItem]
    candidatesConsidered: int


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_mentors(payload: RecommendRequest):
    guard = validate_query(payload.query)
    if not guard.is_allowed:
        return RecommendResponse(
            question=payload.query,
            hasMatches=False,
            summary=guard.reason or "GuidEd only supports career and mentorship inquiries.",
            recommendations=[],
            candidatesConsidered=0
        )

    try:
        result = recommend(
            question=payload.query,
            constraints=payload.constraints,
            top_k=payload.top_k
        )
        return RecommendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")
