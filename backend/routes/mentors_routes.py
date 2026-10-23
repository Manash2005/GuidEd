from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from db.mongo import get_database
from models.mentor_model import MentorResponse

router = APIRouter(prefix="/mentors", tags=["Mentors"])

@router.get("", response_model=List[MentorResponse])
async def list_mentors(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    sector: Optional[str] = Query(None, description="Filter by sector of expertise"),
    seniority: Optional[str] = Query(None, description="Filter by seniority"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Retrieve mentors with optional filtering from MongoDB."""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB connection not available. Please verify your MongoDB Atlas network access."
        )
    filter_query = {}

    if domain:
        filter_query["domain"] = {"$regex": domain, "$options": "i"}
    if sector:
        filter_query["sectorsOfExpertise"] = {"$regex": sector, "$options": "i"}
    if seniority:
        filter_query["seniority"] = seniority

    cursor = db["mentors"].find(filter_query, {"_id": 0}).skip(skip).limit(limit)
    mentors = await cursor.to_list(length=limit)
    return mentors

@router.get("/{mentor_id}", response_model=MentorResponse)
async def get_mentor_by_id(mentor_id: str):
    """Fetch a single mentor by mentorId (e.g. M001)."""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB connection not available. Please verify your MongoDB Atlas network access."
        )
    mentor = await db["mentors"].find_one({"mentorId": mentor_id.upper()}, {"_id": 0})
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor {mentor_id} not found")
    return mentor
