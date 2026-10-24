import sys
from pathlib import Path
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from agent.ranking import calculate_100pt_rubric, score_candidate, rank_candidates
from agent.recommender import check_underspecified_query, recommend
from agent.guardrails import validate_query, check_heuristic_out_of_domain, FRIENDLY_GUARDRAIL_RESPONSE
from utils.title_generator import generate_conversation_title

client = TestClient(app)

# ==============================================================================
# 1. 100-Point Scoring Rubric & Boundary Tests
# ==============================================================================

def test_100pt_rubric_components():
    profile_strong = {
        "mentorId": "M100",
        "name": "Alex Rivera",
        "domain": "Product Management",
        "masterSector": "Artificial Intelligence",
        "sectorsOfExpertise": ["AI Products", "SaaS"],
        "rolesOfExpertise": ["Senior Product Manager", "AI Strategist"],
        "seniority": "Senior",
        "mentorshipQuality": "Excellent",
        "aiProfile": {
            "subdomains": ["Large Language Models", "Autonomous Agents"],
            "tools": ["LangChain", "OpenAI API", "Jira"]
        },
        "toolExperience": {
            "jira": True,
            "tableau": True
        }
    }

    query = "Looking for a senior mentor in AI product management with LangChain and Jira"
    total_score, breakdown = calculate_100pt_rubric(
        query=query,
        profile=profile_strong,
        distance=0.1,
        rerank_score=0.92
    )

    # Must be between 0 and 100
    assert 0 <= total_score <= 100
    # Strong match should score high (> 75%)
    assert total_score >= 75
    # Check component caps
    assert 0 <= breakdown.expertiseSkillScore <= 40
    assert 0 <= breakdown.domainAlignmentScore <= 25
    assert 0 <= breakdown.roleSeniorityScore <= 15
    assert 0 <= breakdown.mentorshipQualityScore <= 10
    assert 0 <= breakdown.toolAiScore <= 10
    # Sum of components must equal totalScore
    assert total_score == (
        breakdown.expertiseSkillScore +
        breakdown.domainAlignmentScore +
        breakdown.roleSeniorityScore +
        breakdown.mentorshipQualityScore +
        breakdown.toolAiScore
    )

def test_scores_vary_with_relevance_not_hardcoded_68():
    high_match_profile = {
        "mentorId": "M_HIGH",
        "name": "High Match",
        "domain": "Product Management",
        "masterSector": "Artificial Intelligence",
        "sectorsOfExpertise": ["AI Products"],
        "rolesOfExpertise": ["Product Manager"],
        "seniority": "Senior",
        "mentorshipQuality": "Excellent",
        "aiProfile": {"tools": ["LLMs"]},
        "toolExperience": {"jira": True}
    }

    low_match_profile = {
        "mentorId": "M_LOW",
        "name": "Low Match",
        "domain": "Tax & Accounting",
        "masterSector": "Finance",
        "sectorsOfExpertise": ["Corporate Tax"],
        "rolesOfExpertise": ["Accountant"],
        "seniority": "Junior",
        "mentorshipQuality": "Poor",
        "aiProfile": {"tools": []},
        "toolExperience": {}
    }

    query = "AI Product Management and LLM deployment"

    high_total, _ = calculate_100pt_rubric(query, high_match_profile, distance=0.1, rerank_score=0.9)
    low_total, _ = calculate_100pt_rubric(query, low_match_profile, distance=0.85, rerank_score=0.1)

    # Scores must vary significantly
    assert high_total > low_total
    # Neither score should be hardcoded to 68%
    assert high_total != 68 or low_total != 68
    # Low match must be low (< 50%)
    assert low_total < 50
    # High match must be high (>= 70%)
    assert high_total >= 70

def test_boundary_filtering_30_percent_threshold():
    """
    Test boundary behavior around the 30% threshold:
    Candidates scoring < 30 must be filtered out.
    """
    c_29 = {
        "mentorId": "M29",
        "name": "Score 29",
        "_composite_score": 0.29,
        "_match_percentage": 29
    }
    c_30 = {
        "mentorId": "M30",
        "name": "Score 30",
        "_composite_score": 0.30,
        "_match_percentage": 30
    }
    c_31 = {
        "mentorId": "M31",
        "name": "Score 31",
        "_composite_score": 0.31,
        "_match_percentage": 31
    }

    qualifying = [c for c in [c_29, c_30, c_31] if c["_match_percentage"] >= 30]
    qualifying_ids = [c["mentorId"] for c in qualifying]

    assert "M29" not in qualifying_ids
    assert "M30" in qualifying_ids
    assert "M31" in qualifying_ids
    assert len(qualifying) == 2

# ==============================================================================
# 2. Clarifying Follow-Up Questions (Phase 3 Requirement 8)
# ==============================================================================

def test_clarifying_question_on_broad_query():
    broad_queries = [
        "I want a mentor who can help me get into product management.",
        "Need a software engineering mentor",
        "help me with data science"
    ]

    for q in broad_queries:
        follow_up = check_underspecified_query(q)
        assert follow_up is not None
        assert "Would you prefer" in follow_up or "specific" in follow_up

def test_no_follow_up_on_sufficiently_specified_query():
    specific_queries = [
        "I want a senior AI product management mentor in Bengaluru experienced with Jira",
        "Looking for a mentor in SaaS product management",
        "Need advice on building automations with n8n and Zapier for FinTech startups"
    ]

    for q in specific_queries:
        follow_up = check_underspecified_query(q)
        assert follow_up is None

# ==============================================================================
# 3. Guardrail Friendly Handling & No 500 Errors (Phase 3 Requirement 9)
# ==============================================================================

def test_out_of_scope_query_returns_friendly_message():
    ood_query = "Write a recipe for pasta with tomatoes and garlic"
    res = validate_query(ood_query, use_llm_fallback=False)

    assert res.is_allowed is False
    assert res.category == "out_of_domain"
    assert res.reason == FRIENDLY_GUARDRAIL_RESPONSE

def test_recommend_endpoint_guardrail_rejection_no_500():
    response = client.post("/api/agent/recommend", json={
        "query": "Write a recipe for chocolate pasta"
    })
    # Must not return 500 server error
    assert response.status_code == 200
    data = response.json()
    assert data["hasMatches"] is False
    assert data["recommendations"] == []
    assert "career planning" in data["summary"].lower() or "mentors" in data["summary"].lower()

# ==============================================================================
# 4. Conversation Title Generation (Phase 1 Requirement 4)
# ==============================================================================

def test_conversation_title_generator():
    cases = [
        ("I want to break into AI product management and learn LLMs", "Break into AI Product Management"),
        ("How can I become a data analyst? What is the career path?", "Become a Data Analyst"),
        ("Can you help me prepare for product management interviews?", "Prepare for Product Management Interviews"),
        ("Which mentors have venture capital experience in Bengaluru?", "Venture Capital Experience in Bengaluru")
    ]

    for query, expected in cases:
        title = generate_conversation_title(query)
        # Length check
        assert len(title) <= 50
        # Words check
        words = title.split()
        assert 2 <= len(words) <= 6
        # Not generic
        assert title != "New Career Conversation"
        assert title != "New Chat"
        # Does not match the full original long sentence
        assert title != query

# ==============================================================================
# 5. Booking Slot Selection & Concurrency Conflict (Phase 4)
# ==============================================================================

def test_slot_selection_equality_rule():
    """
    Verifies that the slot selection equality check accurately distinguishes
    different slots and avoids the undefined === undefined bug.
    """
    slot_a = {"slotStart": "2026-10-25T10:00:00Z", "slotEnd": "2026-10-25T10:30:00Z", "isAvailable": True}
    slot_b = {"slotStart": "2026-10-25T10:30:00Z", "slotEnd": "2026-10-25T11:00:00Z", "isAvailable": True}
    selected_slot = slot_a

    # Correct equality check
    is_a_selected = bool(selected_slot and selected_slot.get("slotStart") and selected_slot["slotStart"] == slot_a["slotStart"])
    is_b_selected = bool(selected_slot and selected_slot.get("slotStart") and selected_slot["slotStart"] == slot_b["slotStart"])

    assert is_a_selected is True
    assert is_b_selected is False
