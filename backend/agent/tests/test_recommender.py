import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.recommender import recommend

DATA_FILE = ROOT / "data" / "mentors.json"

def load_dataset_mentors():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        mentors = json.load(f)
    return {m["mentorId"]: m for m in mentors}

TEST_CASES = [
    {
        "id": "T01_AI_PM",
        "query": "I'm a software professional interested in moving into AI product management. Which mentors are relevant?",
        "constraints": None,
        "expect_matches": True,
        "description": "Semantic recommendation for AI Product Management"
    },
    {
        "id": "T02_WORKFLOWS_N8N",
        "query": "I want advice on building AI workflows and automations with tools such as n8n or Zapier. Who could help?",
        "constraints": None,
        "expect_matches": True,
        "description": "Specific AI tools and workflow automation"
    },
    {
        "id": "T03_QUICK_COMMERCE",
        "query": "I am starting a business in quick commerce and want advice on growth and category management.",
        "constraints": None,
        "expect_matches": True,
        "description": "Sector (Quick Commerce) & role (Growth / Category Management)"
    },
    {
        "id": "T04_VENTURE_CAPITAL",
        "query": "Which mentors have venture capital experience?",
        "constraints": None,
        "expect_matches": True,
        "description": "Domain/sector lookup for Venture Capital"
    },
    {
        "id": "T05_CLIMATE_TECH",
        "query": "I am building a climate-tech or green-tech company. Which mentors have relevant sector experience?",
        "constraints": None,
        "expect_matches": True,
        "description": "Sector expertise in Climate-tech / Green-tech"
    },
    {
        "id": "T06_CYBERSECURITY_NEGATIVE",
        "query": "I need a cybersecurity mentor based in Bengaluru. Who in the dataset matches?",
        "constraints": None,
        "expect_matches": False,
        "description": "Negative query: cybersecurity does not exist in dataset (MUST NOT hallucinate)"
    },
    {
        "id": "T07_VC_SENIOR_CONSTRAINT",
        "query": "Find me a mentor with confirmed seniority of Senior and experience in venture capital.",
        "constraints": {"seniority": "Senior"},
        "expect_matches": True,
        "description": "Hard constraint: Seniority must be Senior + VC"
    },
    {
        "id": "T08_MEDIA_GAMING",
        "query": "I am interested in product management in gaming or media.",
        "constraints": None,
        "expect_matches": True,
        "description": "Product management in niche Media/Gaming sectors"
    }
]

def run_tests():
    dataset = load_dataset_mentors()
    all_dataset_ids = set(dataset.keys())

    print("=" * 70)
    print("RUNNING RECOMMENDER RELEVANCE & HALLUCINATION TEST SUITE")
    print(f"Total test queries: {len(TEST_CASES)} | Total dataset mentors: {len(dataset)}")
    print("=" * 70)

    passed_count = 0

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] Test: {test['id']}")
        print(f"Query: \"{test['query']}\"")
        if test['constraints']:
            print(f"Constraints: {test['constraints']}")

        start_time = time.time()
        result = recommend(test["query"], constraints=test.get("constraints"), top_k=10)
        elapsed = time.time() - start_time

        has_matches = result["hasMatches"]
        recs = result["recommendations"]

        # 1. Check Hallucination of Mentor IDs
        hallucinated_ids = [r["mentorId"] for r in recs if r["mentorId"] not in all_dataset_ids]
        is_hallucination_free = len(hallucinated_ids) == 0

        # 2. Check Name Accuracy against Dataset
        name_mismatches = []
        for r in recs:
            actual = dataset.get(r["mentorId"], {})
            if actual.get("name") != r["name"]:
                name_mismatches.append(f"{r['mentorId']}: got '{r['name']}', expected '{actual.get('name')}'")

        # 3. Check Relevance / Expectation match
        matches_expectation = (has_matches == test["expect_matches"])

        # Determine pass/fail
        test_passed = is_hallucination_free and len(name_mismatches) == 0 and matches_expectation

        if test_passed:
            passed_count += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"Status: {status} (in {elapsed:.2f}s)")
        print(f"Summary: {result['summary']}")
        print(f"Recommendations returned: {len(recs)}")

        if recs:
            for r in recs[:3]:  # Print first 3 for brevity
                print(f"  * {r['mentorId']} ({r['name']})")
                print(f"    Reason: {r['matchReason']}")
                print(f"    Evidence: {r['relevantExperience']}")
                print(f"    Limitations: {r['limitations']}")

        if not is_hallucination_free:
            print(f"  [ERROR] Hallucinated IDs: {hallucinated_ids}")
        if name_mismatches:
            print(f"  [ERROR] Name Mismatches: {name_mismatches}")
        if not matches_expectation:
            print(f"  [ERROR] Expected hasMatches={test['expect_matches']}, got {has_matches}")

        time.sleep(1)  # small pause between calls

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed_count}/{len(TEST_CASES)} passed")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
