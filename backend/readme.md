# 🎯 Retrieval & Search Evaluation Benchmarks

Tracking retrieval quality on 10 fixed benchmark queries (`Q001` - `Q010`) at K=5.

---

### 🔹 Without Reranker (Baseline ChromaDB Vector Search)
- **Hit Rate@5:** 100.0%
- **Mean Recall@5:** 70.7%
- **Mean Precision@5:** 66.0%
- **MRR@5:** 1.000
- **Queries Evaluated:** 10
- **Date:** 2026-10-24 11:50

---

### 🔹 With Reranker (ChromaDB + FlashRank)
- **Hit Rate@5:** 100.0%
- **Mean Recall@5:** 77.9%
- **Mean Precision@5:** 74.0%
- **MRR@5:** 0.900
- **Queries Evaluated:** 10
- **Date:** 2026-10-24 11:59

---

### 🔹 Two-Stage Hybrid (Dense BGE + FlashRank Over-Fetch 25)
- **Hit Rate@5:** 100.0%
- **Mean Recall@5:** 67.9%
- **Mean Precision@5:** 64.0%
- **MRR@5:** 0.950
- **Queries Evaluated:** 10
- **Date:** 2026-10-24 12:16

---

### 🔹 Dense BGE Vector Search (No Reranker)
- **Hit Rate@5:** 100.0%
- **Mean Recall@5:** 55.9%
- **Mean Precision@5:** 54.0%
- **MRR@5:** 0.950
- **Queries Evaluated:** 10
- **Date:** 2026-10-24 12:16

---

