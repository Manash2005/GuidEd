import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ScoreBreakdown(BaseModel):
    semanticScore: float = Field(..., description="Dense semantic and cross-encoder score [0-1]")
    domainSectorScore: float = Field(..., description="Domain and sector relevance score [0-1]")
    roleToolScore: float = Field(..., description="Role and tool match score [0-1]")
    seniorityQualityScore: float = Field(..., description="Seniority and mentorship quality score [0-1]")

class RankingWeights(BaseModel):
    semantic: float = 0.45
    domain_sector: float = 0.25
    role_tool: float = 0.20
    seniority_quality: float = 0.10

def _tokenize(text: str) -> set:
    if not text:
        return set()
    return set(re.findall(r"\b[a-zA-Z0-9_\-\+#]+\b", text.lower()))

def calculate_semantic_score(distance: float, rerank_score: float) -> float:
    # Cosine distance to similarity: clamp(1 - distance, 0, 1)
    sim = max(0.0, min(1.0, 1.0 - distance)) if distance is not None else 0.5
    # Normalize rerank score (typically in [0, 1])
    rr = max(0.0, min(1.0, rerank_score)) if rerank_score is not None else 0.5
    return round(0.7 * rr + 0.3 * sim, 4)

def calculate_domain_sector_score(query_tokens: set, profile: Dict[str, Any]) -> float:
    score = 0.0
    domain = str(profile.get("domain") or "").lower()
    master_sector = str(profile.get("masterSector") or "").lower()
    sectors = [str(s).lower() for s in (profile.get("sectorsOfExpertise") or [])]

    # Domain match
    domain_tokens = _tokenize(domain)
    if domain_tokens and (domain_tokens & query_tokens):
        score += 0.5

    # Sector matches
    sector_tokens = _tokenize(master_sector)
    for s in sectors:
        sector_tokens |= _tokenize(s)

    matching_sectors = sector_tokens & query_tokens
    if matching_sectors:
        score += min(0.5, 0.25 * len(matching_sectors))

    return round(min(1.0, score), 4)

def calculate_role_tool_score(query_tokens: set, profile: Dict[str, Any]) -> float:
    score = 0.0

    # Roles of expertise
    roles = [str(r).lower() for r in (profile.get("rolesOfExpertise") or [])]
    role_tokens = set()
    for r in roles:
        role_tokens |= _tokenize(r)

    matching_roles = role_tokens & query_tokens
    if matching_roles:
        score += min(0.5, 0.25 * len(matching_roles))

    # Tools
    ai_profile = profile.get("aiProfile") or {}
    ai_tools = [str(t).lower() for t in (ai_profile.get("tools") or [])]
    tool_tokens = set()
    for t in ai_tools:
        tool_tokens |= _tokenize(t)

    # Boolean tool experience flags
    tool_exp = profile.get("toolExperience") or {}
    for tool_name, active in tool_exp.items():
        if active:
            tool_tokens.add(str(tool_name).lower())

    matching_tools = tool_tokens & query_tokens
    if matching_tools:
        score += min(0.5, 0.25 * len(matching_tools))

    return round(min(1.0, score), 4)

def calculate_seniority_quality_score(profile: Dict[str, Any]) -> float:
    seniority = str(profile.get("seniority") or "").strip().lower()
    quality = str(profile.get("mentorshipQuality") or "").strip().lower()

    sen_score = 0.2
    if seniority == "senior":
        sen_score = 0.6
    elif seniority == "mid-career":
        sen_score = 0.4

    qual_score = 0.05
    if quality == "excellent":
        qual_score = 0.4
    elif quality == "good":
        qual_score = 0.3
    elif quality == "average":
        qual_score = 0.15

    return round(min(1.0, sen_score + qual_score), 4)

def score_candidate(
    query: str,
    profile: Dict[str, Any],
    distance: float,
    rerank_score: float,
    weights: Optional[RankingWeights] = None
) -> tuple[float, ScoreBreakdown]:
    w = weights or RankingWeights()
    q_tokens = _tokenize(query)

    sem_score = calculate_semantic_score(distance, rerank_score)
    ds_score = calculate_domain_sector_score(q_tokens, profile)
    rt_score = calculate_role_tool_score(q_tokens, profile)
    sq_score = calculate_seniority_quality_score(profile)

    composite = (
        w.semantic * sem_score +
        w.domain_sector * ds_score +
        w.role_tool * rt_score +
        w.seniority_quality * sq_score
    )

    breakdown = ScoreBreakdown(
        semanticScore=sem_score,
        domainSectorScore=ds_score,
        roleToolScore=rt_score,
        seniorityQualityScore=sq_score
    )

    return round(composite, 4), breakdown

def rank_candidates(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 5,
    weights: Optional[RankingWeights] = None
) -> List[Dict[str, Any]]:
    scored = []
    for c in candidates:
        distance = c.get("_retrieval_distance", 0.5)
        rerank_score = c.get("_rerank_score", 0.5)
        comp_score, breakdown = score_candidate(query, c, distance, rerank_score, weights)

        scored_item = c.copy()
        scored_item["_composite_score"] = comp_score
        scored_item["_score_breakdown"] = breakdown.model_dump()
        scored.append(scored_item)

    scored.sort(key=lambda x: x["_composite_score"], reverse=True)
    return scored[:top_k]
