import json
import os
import re
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
# Clarifying Follow-Up Heuristic (Phase 3 Requirement 8)
# ==============================================================================

BROAD_CAREER_TARGETS = [
    r"\bproduct\s+management\b",
    r"\bsoftware\s+engineering\b",
    r"\bdata\s+science\b",
    r"\bdata\s+analytics?\b",
    r"\bmarketing\b",
    r"\bventure\s+capital\b",
    r"\bconsulting\b",
    r"\bdesign\b"
]

SPECIFIC_QUALIFIERS = [
    # Subdomains & sectors
    r"\bai\b", r"\bllms?\b", r"\bsaas\b", r"\bb2b\b", r"\bb2c\b", r"\bfintech\b",
    r"\bhealthtech\b", r"\bclimate\b", r"\bedtech\b", r"\bquick\s+commerce\b",
    r"\be-commerce\b", r"\bgenai\b",
    # Tools
    r"\bjira\b", r"\btableau\b", r"\bhubspot\b", r"\bmixpanel\b", r"\bpython\b",
    r"\bsql\b", r"\bn8n\b", r"\bzapier\b", r"\bfigma\b", r"\bexcel\b",
    # Seniority / roles
    r"\bsenior\b", r"\blead\b", r"\bdirector\b", r"\bvp\b", r"\bhead\b", r"\bprincipal\b",
    # Locations
    r"\bbengaluru\b", r"\bbangalore\b", r"\bmumbai\b", r"\bdelhi\b", r"\bsan\s+francisco\b",
    r"\bremote\b"
]

def check_underspecified_query(question: str, constraints: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Checks if a student's request lacks important constraints.
    If underspecified, returns a helpful, concise follow-up question.
    """
    if constraints and any(constraints.values()):
        return None  # Constraints already provided explicitly

    q_lower = question.lower().strip()
    words = re.findall(r"\b\w+\b", q_lower)

    # If the user provided detailed description (> 14 words), treat as sufficiently specified
    if len(words) > 14:
        return None

    # Check if query contains any specific qualifier (subdomain, tool, seniority, location)
    has_qualifier = any(re.search(pat, q_lower) for pat in SPECIFIC_QUALIFIERS)
    if has_qualifier:
        return None

    # Check if query matches a broad generic target
    for broad_pat in BROAD_CAREER_TARGETS:
        if re.search(broad_pat, q_lower):
            if "product" in broad_pat:
                return (
                    "Would you prefer a mentor with experience in AI product management, SaaS, or general consumer tech? "
                    "Is there a specific location, company type, or tool (such as Jira or Mixpanel) you want them to specialize in?"
                )
            elif "software" in broad_pat:
                return (
                    "Would you prefer a mentor focusing on backend systems, frontend architectures, or AI/ML engineering? "
                    "Are there specific languages or frameworks (e.g. Python, React, Cloud) you'd like them to have?"
                )
            elif "data" in broad_pat:
                return (
                    "Are you interested in machine learning engineering, business intelligence, or general data analytics? "
                    "Are there specific tools like SQL, Tableau, or PyTorch you want help with?"
                )
            else:
                return (
                    "To help find the most relevant mentor, do you have a preference for industry sector, "
                    "seniority level, or specific tools you want to master?"
                )

    return None


# ==============================================================================
# Metadata Pre-Filter Builder
# ==============================================================================

def build_chroma_where(constraints: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Translates user constraints into a ChromaDB 'where' filter for pre-filtering.
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
# Main Recommendation Function
# ==============================================================================

RECOMMENDER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Mentor Connect's expert mentor matching assistant.
Your task is to analyze candidate mentor profiles retrieved from the dataset and recommend top mentors who genuinely match the student's question.

CRITICAL RULES:
1. STRICT FACTUAL GROUNDING: Rely ONLY on facts stated in the candidate profiles. Do NOT invent, assume, or extrapolate experience or achievements.
2. NO GENERAL KNOWLEDGE INVENTIONS: Do not decide facts about mentors from general knowledge. If a candidate's profile does not support relevance, DO NOT recommend them.
3. RECOMMEND 2 TO 3 DISTINCT MENTORS:
   - When matching candidates exist in the list, ALWAYS provide 2 to 3 distinct structured mentor recommendations (ranked from strongest to best alternative) so the student has viable choices.
   - Do NOT return just 1 mentor if there are multiple relevant candidates available in the provided list.
4. HONEST NO-MATCH: If none of the candidate profiles match the student's question, return `hasMatches = False`, an empty `recommendations` list, and an honest explanation in `summary`.
5. EVIDENCE & LIMITATIONS:
   - For every match, cite specific evidence in `relevantExperience` (e.g., domain, rolesOfExpertise, sectorsOfExpertise, AI tools).
   - In `limitations`, note missing or unconfirmed details honestly (e.g., 'Seniority is unconfirmed in profile', 'Specific proprietary tools unlisted', or data quality notes).
"""),
    ("human", """Student Question:
{question}

Candidate Mentor Profiles (Top retrieved & reranked):
{candidates_json}

Provide structured recommendations (2-3 distinct mentors if matches exist) based strictly on the above candidates.""")
])


def recommend(
    question: str,
    constraints: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    fetch_k: int = 25
) -> Dict[str, Any]:
    """
    Two-Stage Hybrid Recommendation Pipeline:
    1. Check if request is underspecified; if so, ask targeted follow-up.
    2. Dense Vector Search + ChromaDB metadata pre-filter.
    3. FlashRank Cross-Encoder reranks the pre-filtered candidates.
    4. Deterministic 100-Point Rubric scoring.
    5. Filter out any candidate with match score < 50%.
    6. LLM provides grounded explanations and evidence.
    """
    # Step 0: Check for underspecified query
    follow_up_prompt = check_underspecified_query(question, constraints)
    if follow_up_prompt:
        return {
            "question": question,
            "hasMatches": False,
            "summary": follow_up_prompt,
            "recommendations": [],
            "candidatesConsidered": 0,
            "isFollowUp": True
        }

    vector_store = get_vector_store()
    where_filter = build_chroma_where(constraints)

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
            "summary": "No mentors matched the specified criteria in the database.",
            "recommendations": [],
            "candidatesConsidered": 0,
            "isFollowUp": False
        }

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

    # FlashRank Reranker
    rerank_request = RerankRequest(query=question, passages=passages)
    reranked = ranker.rerank(rerank_request)

    candidate_list = []
    for item in reranked:
        m_id = item["id"]
        profile = candidates_by_id[m_id].copy()
        profile["_rerank_score"] = round(item["score"], 4)
        candidate_list.append(profile)

    # Deterministic 100-Point Ranking
    all_scored = rank_candidates(question, candidate_list, top_k=len(candidate_list))

    # Update candidate lookup with computed scores
    for c in all_scored:
        c_id = c["mentorId"]
        if c_id in candidates_by_id:
            candidates_by_id[c_id]["_composite_score"] = c.get("_composite_score")
            candidates_by_id[c_id]["_score_breakdown"] = c.get("_score_breakdown")
            candidates_by_id[c_id]["_match_percentage"] = c.get("_match_percentage")
            candidates_by_id[c_id]["_rerank_score"] = c.get("_rerank_score")

    # RULE 7: STRICTLY Filter out candidates with score < 50%
    qualifying_candidates = [
        c for c in all_scored
        if (c.get("_match_percentage") or int(round(c.get("_composite_score", 0) * 100))) >= 50
    ]

    if not qualifying_candidates:
        return {
            "question": question,
            "hasMatches": False,
            "summary": "We couldn't find a mentor meeting our 50% relevance threshold for your specific request. Try broadening your criteria, mentioning related industries, or asking about specific skills or tools.",
            "recommendations": [],
            "candidatesConsidered": len(passages),
            "isFollowUp": False
        }

    top_candidates = qualifying_candidates[:top_k]

    # Send top qualifying candidates to LLM for grounded explanation
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

    # Validate mentor IDs and ensure computed scores are preserved
    eligible_ids = {c["mentorId"] for c in top_candidates}
    validated_recommendations = []

    for rec in llm_output.recommendations:
        rec_id = rec.mentorId.strip().upper()
        if rec_id in eligible_ids:
            actual_profile = candidates_by_id[rec_id]
            verified_name = actual_profile.get("name", rec.name)
            match_pct = actual_profile.get("_match_percentage")
            if match_pct is None:
                comp_score = actual_profile.get("_composite_score") or 0.5
                match_pct = int(round(float(comp_score) * 100))

            if match_pct >= 50:
                validated_recommendations.append({
                    "mentorId": rec_id,
                    "name": verified_name,
                    "company": actual_profile.get("company") or "Technology & Innovation",
                    "seniority": actual_profile.get("seniority") or "Experienced Mentor",
                    "domain": actual_profile.get("domain") or "Specialist",
                    "city": actual_profile.get("city") or "Global",
                    "sectorsOfExpertise": actual_profile.get("sectorsOfExpertise") or [],
                    "rolesOfExpertise": actual_profile.get("rolesOfExpertise") or [],
                    "matchReason": rec.matchReason,
                    "relevantExperience": rec.relevantExperience,
                    "limitations": rec.limitations,
                    "compositeScore": actual_profile.get("_composite_score"),
                    "matchPercentage": match_pct,
                    "scoreBreakdown": actual_profile.get("_score_breakdown"),
                    "distance": actual_profile.get("_retrieval_distance"),
                    "rerankScore": actual_profile.get("_rerank_score"),
                    "aiProfile": actual_profile.get("aiProfile"),
                    "toolExperience": actual_profile.get("toolExperience"),
                    "mentorshipQuality": actual_profile.get("mentorshipQuality"),
                    "activities": actual_profile.get("activities") or [],
                    "dataQualityIssues": actual_profile.get("dataQualityIssues") or []
                })

    # If LLM returned fewer than 2 distinct mentors but other qualifying candidates exist, backfill
    if len(validated_recommendations) < min(3, len(top_candidates)):
        already_selected_ids = {r["mentorId"] for r in validated_recommendations}
        for cand in top_candidates:
            if len(validated_recommendations) >= 3:
                break
            cand_id = cand.get("mentorId")
            if cand_id and cand_id not in already_selected_ids:
                cand_profile = candidates_by_id.get(cand_id, cand)
                c_pct = cand_profile.get("_match_percentage")
                if c_pct is None:
                    c_pct = int(round(float(cand_profile.get("_composite_score", 0.5)) * 100))

                if c_pct >= 50:
                    sectors = cand_profile.get("sectorsOfExpertise") or []
                    roles = cand_profile.get("rolesOfExpertise") or []
                    domain = cand_profile.get("domain") or "Domain Specialist"
                    sectors_label = ", ".join(sectors[:2]) if sectors else domain

                    validated_recommendations.append({
                        "mentorId": cand_id,
                        "name": cand_profile.get("name", f"Mentor {cand_id}"),
                        "company": cand_profile.get("company") or "Technology & Innovation",
                        "seniority": cand_profile.get("seniority") or "Experienced Mentor",
                        "domain": domain,
                        "city": cand_profile.get("city") or "Global",
                        "sectorsOfExpertise": sectors,
                        "rolesOfExpertise": roles,
                        "matchReason": f"Specialist in {domain} with verified expertise in {sectors_label}.",
                        "relevantExperience": f"Domain: {domain}. Specialization: {', '.join(roles[:2]) if roles else 'Advisory'}.",
                        "limitations": "Profile details available during consultation.",
                        "compositeScore": cand_profile.get("_composite_score"),
                        "matchPercentage": c_pct,
                        "scoreBreakdown": cand_profile.get("_score_breakdown"),
                        "distance": cand_profile.get("_retrieval_distance"),
                        "rerankScore": cand_profile.get("_rerank_score"),
                        "aiProfile": cand_profile.get("aiProfile"),
                        "toolExperience": cand_profile.get("toolExperience"),
                        "mentorshipQuality": cand_profile.get("mentorshipQuality"),
                        "activities": cand_profile.get("activities") or [],
                        "dataQualityIssues": cand_profile.get("dataQualityIssues") or []
                    })
                    already_selected_ids.add(cand_id)

    # Final sorting by computed matchPercentage descending
    validated_recommendations.sort(key=lambda x: x["matchPercentage"], reverse=True)

    has_matches = len(validated_recommendations) > 0
    summary = llm_output.summary if has_matches else "No mentors met the 50% relevance threshold for this inquiry."

    return {
        "question": question,
        "hasMatches": has_matches,
        "summary": summary,
        "recommendations": validated_recommendations,
        "candidatesConsidered": len(passages),
        "isFollowUp": False
    }


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
        print(f"\n- [{r['mentorId']}] {r['name']} ({r['matchPercentage']}% Match)")
        print(f"  Reason: {r['matchReason']}")
        print(f"  Evidence: {r['relevantExperience']}")
        print(f"  Limitations: {r['limitations']}")
        print(f"  Score Breakdown: {r.get('scoreBreakdown')}")
