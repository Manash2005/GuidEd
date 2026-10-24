import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from agent.recommender import get_llm

FRIENDLY_GUARDRAIL_RESPONSE = (
    "I can help with career planning, professional skills, interview preparation, "
    "and finding mentors. Could you rephrase your question around your career goals?"
)

class GuardrailResult(BaseModel):
    is_allowed: bool
    category: str = "career_inquiry"
    reason: Optional[str] = None

class LLMClassification(BaseModel):
    is_career_related: bool = Field(
        ...,
        description="True if query is related to career, mentorship, jobs, professional skills, or industry advice."
    )
    reason: Optional[str] = Field(
        None,
        description="Brief explanation if rejected, or null if allowed."
    )

INJECTION_PATTERNS = [
    r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|existing)\s+(instructions|prompts|rules|commands)\b",
    r"(?i)\b(system\s+prompt|system\s+instructions|initial\s+prompt)\b",
    r"(?i)\b(reveal|show|print|output|display|repeat)\s+(your|the)?\s*(system|initial|secret)?\s*(prompt|instructions|rules)\b",
    r"(?i)\b(you\s+are\s+now|act\s+as)\s+(an?\s+unrestricted|dan|jailbreak|unfiltered|evil)\b",
    r"(?i)\b(dan\s+mode|jailbreak\s+mode|developer\s+mode)\b",
    r"(?i)(<\s*/?\s*system\s*>|\[\s*INST\s*\]|<<\s*SYS\s*>>|---\s*BEGIN\s+SYSTEM\s+PROMPT)",
    r"(?i)\b(bypass\s+all\s+restrictions|do\s+anything\s+now)\b"
]

OUT_OF_DOMAIN_PATTERNS = [
    r"(?i)\b(recipe\s+for|how\s+to\s+(cook|bake)|ingredients\s+for)\b",
    r"(?i)\b(solve\s+(for\s+x|the\s+equation)|calculate\s+\d+|derivative\s+of|integral\s+of)\b",
    r"(?i)\b(who\s+won\s+the|who\s+is\s+the\s+president\s+of|capital\s+of\s+[A-Za-z]+)\b",
    r"(?i)\b(write\s+a\s+(poem|story|song|joke|essay)\s+about)\b",
    r"(?i)^(write|generate)\s+(a\s+)?(python|javascript|c\+\+|java|bash|sql)?\s*(script|function|code|program)\s+to\s+(scrape|calculate|sort|parse|download)\b"
]

CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a strict career-intent moderation filter for Mentor Connect, a career mentorship platform.
Your job is to determine whether the student query is genuinely about career growth, mentorship, job hunting, skill acquisition, transitions, or industry guidance.

ALLOW:
- Career transitions (e.g. engineer to product manager, sales to tech)
- Seeking mentorship in specific domains, sectors, or companies
- Inquiries about tools/skills in professional contexts (e.g. n8n, SQL, Figma, LangChain)
- Startup advice, founder mentorship, VC fundraising guidance
- Seniority, interview preparation, or career pathways

REJECT:
- Coding homework or arbitrary script generation (e.g., 'write a quicksort in python')
- Math/physics equations or homework
- Cooking recipes, entertainment, sports trivia, news, politics
- Creative fiction, jokes, or non-career inquiries

Be accurate and unbiased. If allowed, set is_career_related to true. If rejected, provide a brief refusal reason."""),
    ("human", "User Query: {query}")
])

def check_prompt_injection(query: str) -> Optional[GuardrailResult]:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query):
            return GuardrailResult(
                is_allowed=False,
                category="prompt_injection",
                reason="Query contains instructions attempting to override system behavior. " + FRIENDLY_GUARDRAIL_RESPONSE
            )
    return None

def check_heuristic_out_of_domain(query: str) -> Optional[GuardrailResult]:
    for pattern in OUT_OF_DOMAIN_PATTERNS:
        if re.search(pattern, query):
            return GuardrailResult(
                is_allowed=False,
                category="out_of_domain",
                reason=FRIENDLY_GUARDRAIL_RESPONSE
            )
    return None

def validate_query(query: str, use_llm_fallback: bool = True) -> GuardrailResult:
    cleaned = query.strip()
    if len(cleaned) < 3:
        return GuardrailResult(
            is_allowed=False,
            category="invalid_length",
            reason="Query is too short. Please provide details about your career question or mentorship goals."
        )

    if len(cleaned) > 1000:
        return GuardrailResult(
            is_allowed=False,
            category="invalid_length",
            reason="Query exceeds the maximum length of 1000 characters."
        )

    # Fast pattern checks
    injection_res = check_prompt_injection(cleaned)
    if injection_res:
        return injection_res

    ood_res = check_heuristic_out_of_domain(cleaned)
    if ood_res:
        return ood_res

    if not use_llm_fallback:
        return GuardrailResult(is_allowed=True, category="career_inquiry")

    # LLM classification for ambiguous queries
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(LLMClassification)
        chain = CLASSIFIER_PROMPT | structured_llm
        result: LLMClassification = chain.invoke({"query": cleaned})

        if not result.is_career_related:
            return GuardrailResult(
                is_allowed=False,
                category="out_of_domain",
                reason=result.reason or FRIENDLY_GUARDRAIL_RESPONSE
            )
        return GuardrailResult(is_allowed=True, category="career_inquiry")
    except Exception as e:
        print(f"Warning: Guardrail LLM classifier failed: {e}")
        return GuardrailResult(is_allowed=True, category="career_inquiry")
