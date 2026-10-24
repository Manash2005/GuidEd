import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Ensure root and backend paths are in sys.path
ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from flashrank import Ranker, RerankRequest
from agent.ranking import rank_candidates, RankingWeights

# Paths
CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"
DATA_FILE = BACKEND_DIR / "data" / "mentors.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Initialize local FlashRank reranker (ms-marco-TinyBERT-L-2-v2)
ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")


# ==============================================================================
# Pydantic Schemas for Structured Output
# ==============================================================================

class MentorRecommendation(BaseModel):
    mentorId: str = Field(
        ...,
        description="The unique mentor ID from the provided candidates (e.g. M033). Must exist in candidates."
    )
    name: str = Field(
        ...,
        description="The mentor's actual name taken directly from the mentor profile."
    )
    matchReason: str = Field(
        ...,
        description="Why the mentor fits the student's specific goal, domain, or inquiry."
    )
    relevantExperience: str = Field(
        ...,
        description="Specific evidence from the profile (domain, sectors, roles of expertise, tools, AI profile)."
    )
    limitations: str = Field(
        ...,
        description="Missing, unconfirmed, or limited information (e.g. seniority is null, no tools listed, data quality issue)."
    )


class RecommendationOutput(BaseModel):
    hasMatches: bool = Field(
        ...,
        description="True if suitable mentors matching the query exist, False otherwise."
    )
    summary: str = Field(
        ...,
        description="A clear summary of findings or an honest explanation of why no match was found."
    )
    recommendations: List[MentorRecommendation] = Field(
        default_factory=list,
        description="List of structured recommendations matching the student's goal."
    )


# ==============================================================================
# Vector Store and LLM Setup
# ==============================================================================

def get_vector_store() -> Chroma:
    """Initialize ChromaDB with BAAI/bge-small-en-v1.5 dense semantic embeddings."""
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return Chroma(
        collection_name="mentors",
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )


def get_llm():
    """Initialize Chat model (preferring fast Groq, falling back to OpenRouter)."""
    if GROQ_API_KEY:
        return ChatOpenAI(
            model="openai/gpt-oss-20b",
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
            temperature=0,
            max_tokens=2048
        )
    elif OPENROUTER_API_KEY:
        return ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct",
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            temperature=0
        )
    else:
        raise ValueError("Neither GROQ_API_KEY nor OPENROUTER_API_KEY is configured in .env")


# ==============================================================================
# Metadata Pre-Filter Builder
# ==============================================================================

def build_chroma_where(constraints: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Translates user constraints into a ChromaDB 'where' filter for pre-filtering.
    Pre-filtering guarantees all retrieved candidates strictly meet the constraints.
    """
    if not constraints:
        return None

    clauses = []
    if "city" in constraints and constraints["city"]:
        clauses.append({"city": constraints["city"].strip().lower()})
    if "seniority" in constraints and constraints["seniority"]:
        clauses.append({"seniority": constraints["seniority"].strip().lower()})
    if "domain" in constraints and constraints["domain"]:
        clauses.append({"domain": constraints["domain"].strip().lower()})
    if "is_ai_native" in constraints and constraints["is_ai_native"] is not None:
        clauses.append({"isAINative": bool(constraints["is_ai_native"])})
    if "built_ai_product" in constraints and constraints["built_ai_product"] is not None:
        clauses.append({"builtAIProductOrWorkflow": bool(constraints["built_ai_product"])})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


# ==============================================================================
# Main Recommendation Function (Two-Stage Hybrid + Pre-Filter + FlashRank)
# ==============================================================================

RECOMMENDER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are GuidEd's expert mentor matching assistant.
Your task is to analyze candidate mentor profiles retrieved from the dataset and recommend only those who genuinely match the student's question.

CRITICAL RULES:
1. STRICT FACTUAL GROUNDING: Rely ONLY on facts stated in the candidate profiles. Do NOT invent, assume, or extrapolate experience or achievements.
2. NO GENERAL KNOWLEDGE INVENTIONS: Do not decide facts about mentors from general knowledge. If a candidate's profile does not support relevance, DO NOT recommend them.
3. HONEST NO-MATCH: If none of the candidate profiles match the student's question (e.g. asking for cybersecurity when none have it), return `hasMatches = False`, an empty `recommendations` list, and an honest explanation in `summary`.
4. EVIDENCE & LIMITATIONS:
   - For every match, cite specific evidence in `relevantExperience` (e.g., domain, rolesOfExpertise, sectorsOfExpertise, AI tools).
   - In `limitations`, note missing or unconfirmed details (e.g., 'Seniority is null in dataset', 'No specific tools recorded', or data quality issues).
"""),
    ("human", """Student Question:
{question}

Candidate Mentor Profiles (Top retrieved & reranked):
{candidates_json}

Provide structured recommendations based strictly on the above candidates.""")
])


def recommend(
    question: str,
    constraints: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    fetch_k: int = 25
) -> Dict[str, Any]:
    """
    Two-Stage Hybrid Recommendation Pipeline:
    1. Pre-filter ChromaDB via 'where' clause on categorical metadata (city, seniority, etc.).
    2. Dense Semantic Search over flattened profiles, over-fetching (fetch_k=25).
    3. FlashRank Cross-Encoder reranks the 25 pre-filtered candidates to pick the top K.
    4. Send top candidates + question to LLM for grounded explanation.
    5. Validate mentor IDs and return structured response.
    """
    vector_store = get_vector_store()

    # Step 1: Build ChromaDB metadata pre-filter
    where_filter = build_chroma_where(constraints)

    # Step 2: Over-fetch candidates with Dense Vector Search + Metadata Pre-Filter
    try:
        raw_results = vector_store.similarity_search_with_score(
            question,
            k=fetch_k,
            filter=where_filter
        )
    except Exception as e:
        print(f"Warning: Vector search with filter failed: {e}. Retrying without filter.")
        raw_results = vector_store.similarity_search_with_score(question, k=fetch_k)

    if not raw_results:
        return {
            "question": question,
            "hasMatches": False,
            "summary": "No mentors matched the specified constraints in the database.",
            "recommendations": [],
            "candidatesConsidered": 0
        }

    # Extract profiles and prepare passages for reranking
    candidates_by_id = {}
    passages = []

    for doc, distance in raw_results:
        meta = doc.metadata or {}
        raw_json_str = meta.get("raw_json")
        if raw_json_str:
            try:
                profile = json.loads(raw_json_str)
            except Exception:
                profile = {"mentorId": meta.get("mentorId"), "name": meta.get("name")}
        else:
            try:
                profile = json.loads(doc.page_content)
            except Exception:
                profile = {"mentorId": meta.get("mentorId"), "name": meta.get("name")}

        mentor_id = profile.get("mentorId")
        if mentor_id and mentor_id not in candidates_by_id:
            profile["_retrieval_distance"] = round(distance, 4)
            candidates_by_id[mentor_id] = profile
            passages.append({
                "id": mentor_id,
                "text": doc.page_content
            })

    # Step 3: FlashRank Reranker (Score all candidate passages)
    rerank_request = RerankRequest(query=question, passages=passages)
    reranked = ranker.rerank(rerank_request)

    candidate_list = []
    for item in reranked:
        m_id = item["id"]
        profile = candidates_by_id[m_id].copy()
        profile["_rerank_score"] = round(item["score"], 4)
        candidate_list.append(profile)

    # Step 4: Explainable Weighted Ranking (Semantic + Domain/Sector + Role/Tool + Seniority/Quality)
    top_candidates = rank_candidates(question, candidate_list, top_k=top_k)

    for c in top_candidates:
        c_id = c["mentorId"]
        if c_id in candidates_by_id:
            candidates_by_id[c_id]["_composite_score"] = c.get("_composite_score")
            candidates_by_id[c_id]["_score_breakdown"] = c.get("_score_breakdown")
            candidates_by_id[c_id]["_rerank_score"] = c.get("_rerank_score")

    if not top_candidates:
        return {
            "question": question,
            "hasMatches": False,
            "summary": "No mentors matched the inquiry after ranking.",
            "recommendations": [],
            "candidatesConsidered": len(passages)
        }

    # Step 5: Send top candidates + question to LLM
    llm = get_llm()
    structured_llm = llm.with_structured_output(RecommendationOutput)

    candidates_prompt_data = [
        {
            "mentorId": m.get("mentorId"),
            "name": m.get("name"),
            "domain": m.get("domain"),
            "company": m.get("company"),
            "masterSector": m.get("masterSector"),
            "sectorsOfExpertise": m.get("sectorsOfExpertise"),
            "rolesOfExpertise": m.get("rolesOfExpertise"),
            "seniority": m.get("seniority"),
            "city": m.get("city"),
            "aiProfile": m.get("aiProfile"),
            "toolExperience": m.get("toolExperience"),
            "mentorshipQuality": m.get("mentorshipQuality"),
            "dataQualityIssues": m.get("dataQualityIssues")
        }
        for m in top_candidates
    ]

    chain = RECOMMENDER_PROMPT | structured_llm
    llm_output: RecommendationOutput = chain.invoke({
        "question": question,
        "candidates_json": json.dumps(candidates_prompt_data, indent=2, ensure_ascii=False)
    })

    # Step 6: Validate mentor IDs and attach explainable ranking scores
    eligible_ids = set(candidates_by_id.keys())
    validated_recommendations = []

    for rec in llm_output.recommendations:
        rec_id = rec.mentorId.strip().upper()
        if rec_id in eligible_ids:
            actual_profile = candidates_by_id[rec_id]
            verified_name = actual_profile.get("name", rec.name)
            validated_recommendations.append({
                "mentorId": rec_id,
                "name": verified_name,
                "matchReason": rec.matchReason,
                "relevantExperience": rec.relevantExperience,
                "limitations": rec.limitations,
                "compositeScore": actual_profile.get("_composite_score"),
                "scoreBreakdown": actual_profile.get("_score_breakdown"),
                "distance": actual_profile.get("_retrieval_distance"),
                "rerankScore": actual_profile.get("_rerank_score")
            })

    has_matches = len(validated_recommendations) > 0 and llm_output.hasMatches
    summary = llm_output.summary or "No confirmed mentor matches found in the dataset for this inquiry."

    return {
        "question": question,
        "hasMatches": has_matches,
        "summary": summary,
        "recommendations": validated_recommendations,
        "candidatesConsidered": len(passages)
    }


# ==============================================================================
# Local CLI Test Runner
# ==============================================================================

if __name__ == "__main__":
    test_query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I'm a software professional interested in moving into AI product management. Which mentors are relevant?"
    )

    print(f"\n==================================================")
    print(f"QUERY: {test_query}")
    print(f"==================================================\n")

    result = recommend(test_query)

    print(f"Has Matches: {result['hasMatches']}")
    print(f"Summary: {result['summary']}\n")
    print(f"Recommendations ({len(result['recommendations'])}):")
    for r in result["recommendations"]:
        print(f"\n- [{r['mentorId']}] {r['name']} (Distance: {r['distance']}, Rerank: {r.get('rerankScore')})")
        print(f"  Reason: {r['matchReason']}")
        print(f"  Evidence: {r['relevantExperience']}")
        print(f"  Limitations: {r['limitations']}")
