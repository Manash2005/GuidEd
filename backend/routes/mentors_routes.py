import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from db.mongo import get_database
from models.mentor_model import MentorPublicResponse

router = APIRouter(prefix="/mentors", tags=["Mentors"])

# Projection to exclude private contact fields from public responses
PUBLIC_PROJECTION = {"_id": 0, "contact": 0, "email": 0, "linkedin": 0}

@router.get("", response_model=List[MentorPublicResponse])
async def list_mentors(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    sector: Optional[str] = Query(None, description="Filter by sector of expertise"),
    seniority: Optional[str] = Query(None, description="Filter by seniority"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB connection not available. Please verify your MongoDB Atlas network access."
        )
    filter_query = {}

    if domain:
        escaped_domain = re.escape(domain.strip())
        filter_query["domain"] = {"$regex": escaped_domain, "$options": "i"}
    if sector:
        escaped_sector = re.escape(sector.strip())
        filter_query["sectorsOfExpertise"] = {"$regex": escaped_sector, "$options": "i"}
    if seniority:
        filter_query["seniority"] = seniority.strip()

    cursor = db["mentors"].find(filter_query, PUBLIC_PROJECTION).skip(skip).limit(limit)
    mentors = await cursor.to_list(length=limit)
    return mentors

@router.get("/{mentor_id}", response_model=MentorPublicResponse)
async def get_mentor_by_id(mentor_id: str):
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB connection not available. Please verify your MongoDB Atlas network access."
        )
    mentor = await db["mentors"].find_one({"mentorId": mentor_id.strip().upper()}, PUBLIC_PROJECTION)
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor {mentor_id} not found")
    return mentor
