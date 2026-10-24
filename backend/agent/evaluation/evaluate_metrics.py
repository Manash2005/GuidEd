import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from flashrank import Ranker, RerankRequest

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "chroma_db"
QUESTIONS = ROOT / "data" / "questions.json"
README = ROOT / "readme.md"

load_dotenv(ROOT / ".env")

embeddings = OpenAIEmbeddings(
    model="nvidia/nemotron-3-embed-1b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    check_embedding_ctx_length=False
)

vector_store = Chroma(
    collection_name="mentors",
    persist_directory=str(DB),
    embedding_function=embeddings
)

# Initialize FlashRank local reranker model
ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")


def log_to_readme(search_type: str, k: int, summary: dict):
    """
    Logs evaluation metrics in a clean row-wise format without tables or question dumps.
    Word-wrap friendly and easy to read.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Clean row-wise entry for this search type
    entry = (
        f"### 🔹 {search_type}\n"
        f"- **Hit Rate@{k}:** {summary['hit_rate']:.1%}\n"
        f"- **Mean Recall@{k}:** {summary['mean_recall']:.1%}\n"
        f"- **Mean Precision@{k}:** {summary['mean_precision']:.1%}\n"
        f"- **MRR@{k}:** {summary['mrr']:.3f}\n"
        f"- **Queries Evaluated:** {summary['num_queries']}\n"
        f"- **Date:** {timestamp}\n\n"
        f"---\n\n"
    )

    header = (
        "# 🎯 Retrieval & Search Evaluation Benchmarks\n\n"
        f"Tracking retrieval quality on 10 fixed benchmark queries (`Q001` - `Q010`) at K={k}.\n\n"
        "---\n\n"
    )

    existing = ""
    if README.exists():
        existing = README.read_text(encoding="utf-8").strip()

    if not existing or "# 🎯 Retrieval & Search Evaluation" not in existing:
        final_content = header + entry
    else:
        target_header = f"### 🔹 {search_type}\n"
        if target_header in existing:
            # Replace existing section for this search type
            sections = existing.split("### 🔹 ")
            new_sections = [sections[0]]
            for s in sections[1:]:
                name = s.split("\n")[0]
                if name.strip() == search_type.strip():
                    new_sections.append(entry.replace("### 🔹 ", ""))
                else:
                    new_sections.append(s)
            final_content = "### 🔹 ".join(new_sections)
        else:
            final_content = existing.rstrip() + "\n\n" + entry

    README.write_text(final_content, encoding="utf-8")
    print(f"\n[INFO] Cleanly logged '{search_type}' metrics to {README}")


def evaluate(use_reranker: bool = True, k: int = 5, fetch_k: int = 15, num_eval_questions: int = 10):
    search_type = "With Reranker (ChromaDB + FlashRank)" if use_reranker else "Without Reranker (Baseline ChromaDB Vector Search)"

    with QUESTIONS.open(encoding="utf-8") as f:
        all_questions = json.load(f)

    # 10 fixed questions with expected targets
    eval_questions = [q for q in all_questions if q.get("expectedMentorIds")][:num_eval_questions]

    print("=" * 65)
    print(f"EVALUATING: {search_type}")
    print(f"Fixed queries: {len(eval_questions)} | Final K = {k}" + (f" | Initial Fetch K = {fetch_k}" if use_reranker else ""))
    print("=" * 65)

    total_recall = 0.0
    total_hits = 0
    total_precision = 0.0
    total_rr = 0.0
    evaluated_count = 0

    for i, q in enumerate(eval_questions, 1):
        q_id = q["id"]
        q_text = q["query"]
        expected = set(q["expectedMentorIds"])

        print(f"[{i}/{len(eval_questions)}] {q_id}...", end=" ", flush=True)

        # Stage 1: Vector retrieval
        candidates = None
        for attempt in range(4):
            try:
                retrieve_limit = fetch_k if use_reranker else k
                candidates = vector_store.similarity_search(q_text, k=retrieve_limit)
                break
            except Exception as e:
                if "429" in str(e) or "Rate limit" in str(e):
                    wait_sec = 15 + attempt * 5
                    print(f"\n  [Rate limit 429] Cooling down {wait_sec}s...", end=" ", flush=True)
                    time.sleep(wait_sec)
                else:
                    raise e

        if candidates is None:
            print("[FAILED]")
            continue

        # Stage 2: Optional FlashRank reranking
        if use_reranker:
            passages = [
                {"id": doc.metadata["mentorId"], "text": doc.page_content}
                for doc in candidates
            ]
            rerank_request = RerankRequest(query=q_text, passages=passages)
            reranked_results = ranker.rerank(rerank_request)
            retrieved = [p["id"] for p in reranked_results[:k]]
        else:
            retrieved = [doc.metadata["mentorId"] for doc in candidates[:k]]

        relevant_found = expected.intersection(retrieved)

        recall = len(relevant_found) / len(expected)
        hit = bool(relevant_found)
        precision = len(relevant_found) / k

        rr = 0.0
        for rank, m_id in enumerate(retrieved, 1):
            if m_id in expected:
                rr = 1.0 / rank
                break

        total_recall += recall
        total_hits += int(hit)
        total_precision += precision
        total_rr += rr
        evaluated_count += 1

        print(f"Recall: {recall:.2f} | Hit: {hit} | RR: {rr:.2f}")

        # Safe sleep between embedding API calls to respect 20 RPM limit
        time.sleep(3.5)

    if evaluated_count == 0:
        print("[ERROR] No queries succeeded.")
        return

    summary = {
        "num_queries": evaluated_count,
        "hit_rate": total_hits / evaluated_count,
        "mean_recall": total_recall / evaluated_count,
        "mean_precision": total_precision / evaluated_count,
        "mrr": total_rr / evaluated_count
    }

    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print(f"Search Type:     {search_type}")
    print(f"Hit Rate@{k}:     {summary['hit_rate']:.1%}")
    print(f"Mean Recall@{k}:  {summary['mean_recall']:.1%}")
    print(f"Mean Prec@{k}:    {summary['mean_precision']:.1%}")
    print(f"MRR@{k}:          {summary['mrr']:.3f}")
    print("=" * 65)

    # Log row-wise metrics to readme.md
    log_to_readme(search_type, k, summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate mentor retrieval strategies")
    parser.add_argument("--no-reranker", action="store_true", help="Run baseline without reranker")
    args = parser.parse_args()

    use_reranker = not args.no_reranker
    evaluate(use_reranker=use_reranker)
