import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

# Paths
CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"
DATA_FILE = BACKEND_DIR / "data" / "mentors.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


#Schemas

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

def get_vector_store() -> Chroma:
    """Initialize persistent ChromaDB vector store with OpenRouter embeddings."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured in .env")

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


def get_llm():
    """Initialize Chat model (preferring fast Groq, falling back to OpenRouter)."""
    if GROQ_API_KEY:
        return ChatOpenAI(
            model="openai/gpt-oss-20b",
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
            temperature=0
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


#constraints

def apply_hard_constraints(candidates: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Filter candidate profiles by hard constraints (if provided).
    Supported constraints:
      - seniority: e.g. "Senior", "Mid-career"
      - city: e.g. "Bengaluru", "San Francisco"
      - domain: substring match
      - is_ai_native: True/False
      - built_ai_product: True/False
      - required_tools: list of tool strings (mentor must have at least one)
    """
    if not constraints:
        return candidates

    filtered = []
    for mentor in candidates:
        # Seniority constraint
        if "seniority" in constraints:
            required_seniority = constraints["seniority"]
            if required_seniority is None and mentor.get("seniority") is not None:
                continue
            if required_seniority is not None and mentor.get("seniority") != required_seniority:
                continue

        # City constraint
        if "city" in constraints:
            if mentor.get("city", "").lower() != constraints["city"].lower():
                continue

        # Domain constraint
        if "domain" in constraints:
            if constraints["domain"].lower() not in mentor.get("domain", "").lower():
                continue

        # AI Native constraint
        if "is_ai_native" in constraints:
            ai_profile = mentor.get("aiProfile") or {}
            if ai_profile.get("isAINative") != constraints["is_ai_native"]:
                continue

        # Built AI Product or Workflow constraint
        if "built_ai_product" in constraints:
            ai_profile = mentor.get("aiProfile") or {}
            if ai_profile.get("builtAIProductOrWorkflow") != constraints["built_ai_product"]:
                continue

        # Required tools constraint
        if "required_tools" in constraints:
            ai_profile = mentor.get("aiProfile") or {}
            mentor_tools = [t.lower() for t in (ai_profile.get("tools") or [])]
            req_tools = [t.lower() for t in constraints["required_tools"]]
            if not any(req_t in mentor_tools for req_t in req_tools):
                continue

        filtered.append(mentor)

    return filtered


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

Candidate Mentor Profiles (Top 10 retrieved):
{candidates_json}

Provide structured recommendations based strictly on the above candidates.""")
])


def recommend(
    question: str,
    constraints: Optional[Dict[str, Any]] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    End-to-end mentor recommendation workflow:
    1. ChromaDB retrieves top mentors
    2. Apply hard constraints (if any)
    3. Send candidates + question to LLM
    4. Validate mentor IDs against retrieved results
    5. Return structured recommendations with reasons
    """
    vector_store = get_vector_store()
    raw_results = vector_store.similarity_search_with_score(question, k=top_k)

    candidates = []
    candidates_by_id = {}
    for doc, distance in raw_results:
        try:
            profile = json.loads(doc.page_content)
        except Exception:
            profile = {"mentorId": doc.metadata.get("mentorId")}

        mentor_id = profile.get("mentorId")
        if mentor_id and mentor_id not in candidates_by_id:
            profile["_retrieval_distance"] = round(distance, 4)
            candidates.append(profile)
            candidates_by_id[mentor_id] = profile

    eligible_candidates = apply_hard_constraints(candidates, constraints)

    if not eligible_candidates:
        return {
            "question": question,
            "hasMatches": False,
            "summary": "No mentors matched the specified constraints in the retrieved dataset.",
            "recommendations": [],
            "candidatesConsidered": 0
        }

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
            "aiProfile": m.get("aiProfile"),
            "toolExperience": m.get("toolExperience"),
            "mentorshipQuality": m.get("mentorshipQuality"),
            "dataQualityIssues": m.get("dataQualityIssues")
        }
        for m in eligible_candidates
    ]

    chain = RECOMMENDER_PROMPT | structured_llm
    llm_output: RecommendationOutput = chain.invoke({
        "question": question,
        "candidates_json": json.dumps(candidates_prompt_data, indent=2, ensure_ascii=False)
    })

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
                "distance": actual_profile.get("_retrieval_distance")
            })

    has_matches = len(validated_recommendations) > 0 and llm_output.hasMatches

    summary = llm_output.summary
    if not has_matches and not summary:
        summary = "No confirmed mentor matches found in the dataset for this inquiry."

    return {
        "question": question,
        "hasMatches": has_matches,
        "summary": summary,
        "recommendations": validated_recommendations,
        "candidatesConsidered": len(eligible_candidates)
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
        print(f"\n- [{r['mentorId']}] {r['name']} (Distance: {r['distance']})")
        print(f"  Reason: {r['matchReason']}")
        print(f"  Evidence: {r['relevantExperience']}")
        print(f"  Limitations: {r['limitations']}")
