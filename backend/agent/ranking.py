import re
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

class ScoreBreakdown(BaseModel):
    """
    100-Point Deterministic Rubric for Mentor Matching:
    - Expertise and skill relevance: max 40 points
    - Domain alignment: max 25 points
    - Role and seniority alignment: max 15 points
    - Mentorship quality: max 10 points
    - Relevant tool or AI experience: max 10 points
    Total: 100 points
    """
    expertiseSkillScore: int = Field(default=0, ge=0, le=40, description="Expertise and skill relevance (0-40)")
    domainAlignmentScore: int = Field(default=0, ge=0, le=25, description="Domain and sector alignment (0-25)")
    roleSeniorityScore: int = Field(default=0, ge=0, le=15, description="Role and seniority alignment (0-15)")
    mentorshipQualityScore: int = Field(default=0, ge=0, le=10, description="Mentorship quality score (0-10)")
    toolAiScore: int = Field(default=0, ge=0, le=10, description="Relevant tool or AI experience (0-10)")
    totalScore: int = Field(default=0, ge=0, le=100, description="Total match score out of 100")

    # Normalized float representations for downstream compatibility
    semanticScore: float = Field(default=0.0, description="Normalized dense semantic score [0-1]")
    domainSectorScore: float = Field(default=0.0, description="Normalized domain score [0-1]")
    roleToolScore: float = Field(default=0.0, description="Normalized role & tool score [0-1]")
    seniorityQualityScore: float = Field(default=0.0, description="Normalized seniority & quality score [0-1]")

class RankingWeights(BaseModel):
    semantic: float = 0.40
    domain_sector: float = 0.25
    role_tool: float = 0.15
    seniority_quality: float = 0.20

# Canonical term expansions
CANONICAL_SYNONYMS = {
    "ai": {"ai", "artificial", "intelligence", "genai", "llm", "llms"},
    "artificial": {"ai", "artificial", "intelligence"},
    "intelligence": {"ai", "artificial", "intelligence"},
    "llm": {"llm", "llms", "ai"},
    "llms": {"llm", "llms", "ai"},
    "product": {"product", "pm"},
    "manager": {"manager", "management", "pm"},
    "management": {"manager", "management", "pm"},
    "engineer": {"engineer", "engineering", "dev", "developer"},
    "engineering": {"engineer", "engineering", "dev", "developer"},
    "analyst": {"analyst", "analytics", "analysis"},
    "analytics": {"analyst", "analytics", "analysis"}
}

def _tokenize(text: str) -> set:
    if not text:
        return set()
    tokens = set(re.findall(r"\b[a-zA-Z0-9_\-\+#]+\b", text.lower()))
    expanded = set(tokens)
    for t in tokens:
        if t in CANONICAL_SYNONYMS:
            expanded |= CANONICAL_SYNONYMS[t]
        # Basic plural strip (e.g. tools -> tool)
        if len(t) > 3 and t.endswith("s"):
            expanded.add(t[:-1])
    return expanded

def calculate_semantic_score(distance: Optional[float], rerank_score: Optional[float]) -> float:
    sim = max(0.0, min(1.0, 1.0 - distance)) if distance is not None else 0.5
    rr = max(0.0, min(1.0, rerank_score)) if rerank_score is not None else 0.5
    return round(0.7 * rr + 0.3 * sim, 4)

def calculate_domain_sector_score(query_tokens: set, profile: Dict[str, Any]) -> float:
    score = 0.0
    domain = str(profile.get("domain") or "").lower()
    master_sector = str(profile.get("masterSector") or "").lower()
    sectors = [str(s).lower() for s in (profile.get("sectorsOfExpertise") or [])]

    domain_tokens = _tokenize(domain)
    if domain_tokens and (domain_tokens & query_tokens):
        score += 0.5

    sector_tokens = _tokenize(master_sector)
    for s in sectors:
        sector_tokens |= _tokenize(s)

    matching_sectors = sector_tokens & query_tokens
    if matching_sectors:
        score += min(0.5, 0.25 * len(matching_sectors))

    return round(min(1.0, score), 4)

def calculate_role_tool_score(query_tokens: set, profile: Dict[str, Any]) -> float:
    score = 0.0

    roles = [str(r).lower() for r in (profile.get("rolesOfExpertise") or [])]
    role_tokens = set()
    for r in roles:
        role_tokens |= _tokenize(r)

    matching_roles = role_tokens & query_tokens
    if matching_roles:
        score += min(0.5, 0.25 * len(matching_roles))

    ai_profile = profile.get("aiProfile") or {}
    ai_tools = [str(t).lower() for t in (ai_profile.get("tools") or [])]
    tool_tokens = set()
    for t in ai_tools:
        tool_tokens |= _tokenize(t)

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

def calculate_100pt_rubric(
    query: str,
    profile: Dict[str, Any],
    distance: Optional[float] = None,
    rerank_score: Optional[float] = None
) -> Tuple[int, ScoreBreakdown]:
    """
    Calculates the explainable 100-point rubric:
    1. Expertise and skill relevance: max 40 points
    2. Domain alignment: max 25 points
    3. Role and seniority alignment: max 15 points
    4. Mentorship quality: max 10 points
    5. Relevant tool or AI experience: max 10 points
    """
    q_tokens = _tokenize(query)

    # 1. Expertise and Skill Relevance (Max 40 points)
    sem_norm = calculate_semantic_score(distance, rerank_score)
    retrieval_pts = round(sem_norm * 25)

    roles = [str(r).lower() for r in (profile.get("rolesOfExpertise") or [])]
    sectors = [str(s).lower() for s in (profile.get("sectorsOfExpertise") or [])]
    expertise_tokens = set()
    for r in roles:
        expertise_tokens |= _tokenize(r)
    for s in sectors:
        expertise_tokens |= _tokenize(s)

    matching_expertise = expertise_tokens & q_tokens
    explicit_pts = min(15, len(matching_expertise) * 5)
    expertise_skill_pts = min(40, max(0, retrieval_pts + explicit_pts))

    # 2. Domain Alignment (Max 25 points)
    domain_pts = 0
    domain = str(profile.get("domain") or "").strip().lower()
    master_sector = str(profile.get("masterSector") or "").strip().lower()
    domain_tokens = _tokenize(domain)
    master_tokens = _tokenize(master_sector)

    if domain:
        if domain_tokens & q_tokens:
            domain_pts += 15
        elif any(dt in query.lower() for dt in domain_tokens if len(dt) > 2):
            domain_pts += 12
    else:
        domain_pts += 5  # Neutral missing

    if master_sector:
        if master_tokens & q_tokens:
            domain_pts += 10
        elif any(mt in query.lower() for mt in master_tokens if len(mt) > 2):
            domain_pts += 8

    domain_pts = min(25, max(0, domain_pts))

    # 3. Role and Seniority Alignment (Max 15 points)
    role_pts = 0
    roles_tokens = set()
    for r in roles:
        roles_tokens |= _tokenize(r)

    if roles_tokens & q_tokens:
        role_pts += min(7, len(roles_tokens & q_tokens) * 3)

    seniority = str(profile.get("seniority") or "").strip().lower()
    wants_senior = bool(q_tokens & {"senior", "lead", "director", "vp", "head", "principal", "experienced"})

    if seniority == "senior":
        sen_pts = 8
    elif seniority == "mid-career":
        sen_pts = 5 if wants_senior else 7
    elif not seniority:
        sen_pts = 4
    else:
        sen_pts = 3

    role_seniority_pts = min(15, max(0, role_pts + sen_pts))

    # 4. Mentorship Quality (Max 10 points)
    quality = str(profile.get("mentorshipQuality") or "").strip().lower()
    if quality == "excellent":
        quality_pts = 10
    elif quality == "good":
        quality_pts = 8
    elif quality == "average":
        quality_pts = 5
    elif not quality:
        quality_pts = 4
    else:
        quality_pts = 2

    quality_pts = min(10, max(0, quality_pts))

    # 5. Relevant Tool or AI Experience (Max 10 points)
    tool_pts = 0
    ai_profile = profile.get("aiProfile") or {}
    ai_tools = [str(t).lower() for t in (ai_profile.get("tools") or [])]
    ai_subdomains = [str(s).lower() for s in (ai_profile.get("subdomains") or [])]
    tool_tokens = set()
    for t in ai_tools:
        tool_tokens |= _tokenize(t)
    for s in ai_subdomains:
        tool_tokens |= _tokenize(s)

    tool_exp = profile.get("toolExperience") or {}
    for tool_name, active in tool_exp.items():
        if active:
            tool_tokens.add(str(tool_name).lower())

    matching_tools = tool_tokens & q_tokens
    if matching_tools:
        tool_pts += min(10, len(matching_tools) * 5)
    else:
        if tool_tokens:
            tool_pts += 3

    tool_ai_pts = min(10, max(0, tool_pts))

    # Total Sum
    total_pts = expertise_skill_pts + domain_pts + role_seniority_pts + quality_pts + tool_ai_pts
    total_pts = min(100, max(0, total_pts))

    breakdown = ScoreBreakdown(
        expertiseSkillScore=expertise_skill_pts,
        domainAlignmentScore=domain_pts,
        roleSeniorityScore=role_seniority_pts,
        mentorshipQualityScore=quality_pts,
        toolAiScore=tool_ai_pts,
        totalScore=total_pts,
        semanticScore=sem_norm,
        domainSectorScore=calculate_domain_sector_score(q_tokens, profile),
        roleToolScore=calculate_role_tool_score(q_tokens, profile),
        seniorityQualityScore=calculate_seniority_quality_score(profile)
    )

    return total_pts, breakdown

def score_candidate(
    query: str,
    profile: Dict[str, Any],
    distance: Optional[float] = None,
    rerank_score: Optional[float] = None,
    weights: Optional[RankingWeights] = None
) -> tuple[float, ScoreBreakdown]:
    total_score, breakdown = calculate_100pt_rubric(
        query=query,
        profile=profile,
        distance=distance,
        rerank_score=rerank_score
    )
    composite = round(total_score / 100.0, 4)
    return composite, breakdown

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
        scored_item["_match_percentage"] = breakdown.totalScore
        scored.append(scored_item)

    scored.sort(key=lambda x: x["_composite_score"], reverse=True)
    return scored[:top_k]
