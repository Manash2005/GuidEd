import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from config import CHROMA_DIR, OPENROUTER_API_KEY
from db.mongo import get_database

router = APIRouter(prefix="/agent", tags=["AI Agent & Recommendations"])

class RecommendRequest(BaseModel):
    query: str
    top_k: int = 5

class MentorMatch(BaseModel):
    mentorId: str
    distance: float
    mentorData: dict

class RecommendResponse(BaseModel):
    query: str
    count: int
    matches: List[MentorMatch]

def get_vector_store():
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    embeddings = OpenAIEmbeddings(
        model="nvidia/nemotron-3-embed-1b:free",
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        check_embedding_ctx_length=False
    )

    return Chroma(
        collection_name="mentors",
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

@router.post("/recommend", response_model=RecommendResponse)
async def recommend_mentors(payload: RecommendRequest):
    """Semantic vector search over mentors based on query text."""
    try:
        vector_store = get_vector_store()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize vector store: {str(e)}")

    try:
        results = vector_store.similarity_search_with_score(payload.query, k=payload.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    db = get_database()
    matches = []

    for doc, distance in results:
        mentor_id = doc.metadata.get("mentorId")
        # Try to enrich from MongoDB if available, fallback to doc content
        mentor_record = None
        if db:
            mentor_record = await db["mentors"].find_one({"mentorId": mentor_id}, {"_id": 0})
        if not mentor_record:
            try:
                mentor_record = json.loads(doc.page_content)
            except Exception:
                mentor_record = {"mentorId": mentor_id}

        matches.append(
            MentorMatch(
                mentorId=mentor_id,
                distance=round(distance, 4),
                mentorData=mentor_record
            )
        )

    return RecommendResponse(
        query=payload.query,
        count=len(matches),
        matches=matches
    )
