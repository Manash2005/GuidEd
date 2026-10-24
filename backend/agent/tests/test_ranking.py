import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.ranking import (
    calculate_semantic_score,
    calculate_domain_sector_score,
    calculate_role_tool_score,
    calculate_seniority_quality_score,
    score_candidate,
    rank_candidates,
    RankingWeights,
    _tokenize
)

def test_tokenize():
    text = "AI Product Manager in E-commerce & FinTech!"
    tokens = _tokenize(text)
    assert "ai" in tokens
    assert "product" in tokens
    assert "manager" in tokens
    assert "e-commerce" in tokens
    assert "fintech" in tokens

def test_semantic_score_calculation():
    # Close distance (0.1) and high rerank score (0.9)
    score = calculate_semantic_score(distance=0.1, rerank_score=0.9)
    assert 0.0 <= score <= 1.0
    assert score > 0.8

    # Far distance (0.9) and low rerank score (0.1)
    low_score = calculate_semantic_score(distance=0.9, rerank_score=0.1)
    assert low_score < 0.3

def test_domain_sector_score():
    profile = {
        "domain": "Product Management",
        "masterSector": "Quick Commerce",
        "sectorsOfExpertise": ["E-commerce", "D2C"]
    }
    query_tokens = _tokenize("Need mentorship in Product Management within quick commerce")
    score = calculate_domain_sector_score(query_tokens, profile)
    assert score >= 0.75

    unrelated_query = _tokenize("Healthcare nursing and clinical surgery")
    zero_score = calculate_domain_sector_score(unrelated_query, profile)
    assert zero_score == 0.0

def test_role_tool_score():
    profile = {
        "rolesOfExpertise": ["Product Management", "AI and Analytics"],
        "aiProfile": {
            "tools": ["n8n", "Zapier", "Make"]
        },
        "toolExperience": {
            "tableau": True,
            "jira": False
        }
    }
    query_tokens = _tokenize("Building automations with n8n and Tableau")
    score = calculate_role_tool_score(query_tokens, profile)
    assert score > 0.4

def test_seniority_quality_score():
    senior_excellent = {
        "seniority": "Senior",
        "mentorshipQuality": "Excellent"
    }
    high_score = calculate_seniority_quality_score(senior_excellent)
    assert high_score == 1.0

    unspecified_poor = {
        "seniority": None,
        "mentorshipQuality": "Poor"
    }
    low_score = calculate_seniority_quality_score(unspecified_poor)
    assert low_score < 0.3

def test_score_candidate_and_breakdown():
    profile = {
        "mentorId": "M001",
        "name": "Mentor One",
        "domain": "Product Management",
        "masterSector": "Quick Commerce",
        "sectorsOfExpertise": ["Quick Commerce"],
        "rolesOfExpertise": ["Category Management"],
        "seniority": "Senior",
        "mentorshipQuality": "Excellent",
        "aiProfile": {"tools": ["n8n"]}
    }
    query = "Quick commerce category management with n8n"
    composite, breakdown = score_candidate(
        query=query,
        profile=profile,
        distance=0.15,
        rerank_score=0.88
    )

    assert 0.0 <= composite <= 1.0
    assert breakdown.semanticScore > 0.0
    assert breakdown.domainSectorScore > 0.0
    assert breakdown.roleToolScore > 0.0
    assert breakdown.seniorityQualityScore == 1.0

def test_rank_candidates_ordering():
    candidates = [
        {
            "mentorId": "M_GENERIC",
            "name": "Generic Mentor",
            "domain": "Accounting",
            "masterSector": "Finance",
            "sectorsOfExpertise": ["Tax"],
            "rolesOfExpertise": ["Auditing"],
            "seniority": "Mid-career",
            "mentorshipQuality": "Average",
            "_retrieval_distance": 0.4,
            "_rerank_score": 0.3
        },
        {
            "mentorId": "M_MATCH",
            "name": "Perfect Match Mentor",
            "domain": "Product Management",
            "masterSector": "Quick Commerce",
            "sectorsOfExpertise": ["Quick Commerce", "E-commerce"],
            "rolesOfExpertise": ["Growth", "Category Management"],
            "seniority": "Senior",
            "mentorshipQuality": "Excellent",
            "_retrieval_distance": 0.1,
            "_rerank_score": 0.95
        }
    ]

    ranked = rank_candidates("Quick commerce growth and category management", candidates, top_k=2)
    assert len(ranked) == 2
    assert ranked[0]["mentorId"] == "M_MATCH"
    assert ranked[0]["_composite_score"] > ranked[1]["_composite_score"]
    assert "_score_breakdown" in ranked[0]
