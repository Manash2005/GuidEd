import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from agent.ranking import rank_candidates
from agent.recommender import rerank_passages

DB = ROOT / "data" / "chroma_db"
QUESTIONS = ROOT / "data" / "questions.json"
README = ROOT / "readme.md"

load_dotenv(ROOT / ".env")

# Dense Semantic Embeddings: BAAI/bge-small-en-v1.5 (runs locally on CPU via ONNX)
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

vector_store = Chroma(
    collection_name="mentors",
    persist_directory=str(DB),
    embedding_function=embeddings
)



def log_to_readme(search_type: str, k: int, summary: dict):
    """
    Logs evaluation metrics in a clean row-wise format without tables or question dumps.
    Word-wrap friendly and easy to read.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

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


def evaluate(strategy: str = "weighted", k: int = 5, fetch_k: int = 25, num_eval_questions: int = 10):
    if strategy == "weighted":
        search_type = "Explainable Weighted Ranking (Dense BGE + FlashRank + Weighted Score)"
    elif strategy == "hybrid":
        search_type = "Two-Stage Hybrid (Dense BGE + FlashRank Over-Fetch 25)"
    else:
        search_type = "Dense BGE Vector Search (No Reranker)"

    with QUESTIONS.open(encoding="utf-8") as f:
        all_questions = json.load(f)

    eval_questions = [q for q in all_questions if q.get("expectedMentorIds")][:num_eval_questions]

    print("=" * 65)
    print(f"EVALUATING: {search_type}")
    print(f"Fixed queries: {len(eval_questions)} | Final K = {k}" + (f" | Over-fetch Candidate Pool = {fetch_k}" if strategy != "baseline" else ""))
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

        retrieve_limit = fetch_k if strategy != "baseline" else k
        raw_results = vector_store.similarity_search_with_score(q_text, k=retrieve_limit)

        if not raw_results:
            print("[FAILED]")
            continue

        if strategy == "baseline":
            retrieved = [doc.metadata["mentorId"] for doc, _ in raw_results[:k]]
        elif strategy == "hybrid":
            passages = [
                {"id": doc.metadata["mentorId"], "text": doc.page_content}
                for doc, _ in raw_results
            ]
            reranked_results = rerank_passages(q_text, passages)
            retrieved = [p["id"] for p in reranked_results[:k]]
        else:
            # Weighted strategy: FlashRank rerank + explainable weighted scoring
            candidates_by_id = {}
            passages = []
            for doc, dist in raw_results:
                meta = doc.metadata or {}
                raw_json = meta.get("raw_json")
                if raw_json:
                    try:
                        prof = json.loads(raw_json)
                    except Exception:
                        prof = {"mentorId": meta.get("mentorId"), "name": meta.get("name")}
                else:
                    prof = {"mentorId": meta.get("mentorId"), "name": meta.get("name")}

                m_id = prof.get("mentorId")
                if m_id and m_id not in candidates_by_id:
                    prof["_retrieval_distance"] = dist
                    candidates_by_id[m_id] = prof
                    passages.append({"id": m_id, "text": doc.page_content})

            reranked_results = rerank_passages(q_text, passages)

            cand_list = []
            for item in reranked_results:
                m_id = item["id"]
                prof = candidates_by_id[m_id].copy()
                prof["_rerank_score"] = item["score"]
                cand_list.append(prof)

            ranked = rank_candidates(q_text, cand_list, top_k=k)
            retrieved = [c["mentorId"] for c in ranked]

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

    log_to_readme(search_type, k, summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate mentor retrieval strategies")
    parser.add_argument("--strategy", choices=["weighted", "hybrid", "baseline"], default="weighted")
    parser.add_argument("--no-reranker", action="store_true", help="Run baseline without reranker")
    args = parser.parse_args()

    strat = "baseline" if args.no_reranker else args.strategy
    evaluate(strategy=strat)
