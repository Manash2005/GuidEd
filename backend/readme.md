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

### 🔹 Explainable Weighted Ranking (Dense BGE + FlashRank + Weighted Score)
- **Hit Rate@5:** 100.0%
- **Mean Recall@5:** 64.4%
- **Mean Precision@5:** 60.0%
- **MRR@5:** 0.950
- **Queries Evaluated:** 10
- **Date:** 2026-10-24 12:50

---

# 🚀 GuidEd Platform Architecture & Feature Reference

GuidEd is an enterprise-grade AI mentorship matching and scheduling platform built with FastAPI, LangChain, ChromaDB, and MongoDB.

### 🛡️ Security & Hardening Baseline
- **Student Authentication:** Native bcrypt password hashing (12 work rounds) and signed JWT tokens with expiry enforcement.
- **PII Masking:** Mentor contact, phone numbers, and email addresses are masked across all public endpoints (`MentorPublicResponse`).
- **Input Sanitization:** Regex-based query sanitization prevents MongoDB regex injection DoS.
- **Security Headers:** Strict Transport Security, X-Frame-Options (DENY), X-Content-Type-Options (nosniff), Referrer-Policy, and X-XSS-Protection.
- **Sliding-Window Rate Limiter:** Protects authentication and heavy recommendation routes against brute-force and resource exhaustion (HTTP 429).

### 🤖 Career Guardrails & Prompt Injection Defense
- Multi-tier validation filters DAN mode exploits, system prompt leakage, and roleplay hijacking.
- Heuristic out-of-domain rejection for non-career queries (recipes, math, poetry, sports).
- Safe structured fallback refusal with friendly career-focused guidance.

### ⚖️ Explainable Weighted Ranking Engine
- Two-stage hybrid retrieval combines dense vector embeddings (`BAAI/bge-small-en-v1.5`) with FlashRank cross-encoder reranking.
- Transparent score breakdown with weighted components:
  - Semantic Match (45%)
  - Domain & Sector Overlap (25%)
  - Role & Tool Synergy (20%)
  - Seniority & Mentorship Quality (10%)

### 💬 Chat Conversations & Message Persistence
- Authenticated, isolated conversation threads stored in MongoDB.
- Per-user ownership isolation preventing unauthorized cross-user access.
- Automated contextual recommendations attached to multi-turn dialogue.

### 📅 Booking Engine & Double-Booking Prevention
- Dynamic 30-minute time slot generation with real-time availability checks.
- Atomic concurrency control preventing both mentor overlap and student schedule collisions (HTTP 409 Conflict).
- Slot release upon booking cancellation.

### 📹 Google Calendar & Google Meet Integration
- OAuth 2.0 refresh token exchange for automated event generation on Google Calendar.
- Native Google Meet video conference link creation via `conferenceDataVersion=1`.
- Clean calendar event deletion upon cancellation with deterministic fallback when unconfigured.

### ✉️ Transactional Notifications & Idempotency
- Responsive HTML and plaintext templates for session confirmations and cancellations.
- Idempotency key tracking in MongoDB (`notifications` collection) preventing duplicate email dispatch on network retries.
- Production SMTP integration with simulated fallback for local development.

---

# 🧪 Automated Test Verification

Total Tests Passing: 60 / 60 (100% Pass Rate)

- `agent/tests/test_guardrails.py`: 21 passed (injection defense, boundary validation, career queries)
- `agent/tests/test_ranking.py`: 7 passed (ranking formula, component breakdown, ordering)
- `tests/test_auth.py`: 6 passed (bcrypt hashing, JWT tokens, expiry, PII masking)
- `tests/test_booking.py`: 4 passed (slot generation, double-booking prevention, cross-user isolation)
- `tests/test_calendar.py`: 6 passed (OAuth refresh, live Google Meet link generation, deletion)
- `tests/test_chat.py`: 8 passed (multi-turn threads, ownership security, deletion)
- `tests/test_e2e_lifecycle.py`: 3 passed (security headers, rate limiting, full student lifecycle)
- `tests/test_email.py`: 5 passed (template rendering, idempotency deduplication, async delivery)

