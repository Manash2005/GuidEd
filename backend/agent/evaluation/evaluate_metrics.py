import os
import json
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "chroma_db"
QUESTIONS = ROOT / "data" / "questions.json"

load_dotenv(ROOT / ".env")
embeddings = OpenAIEmbeddings(
    model="nvidia/nemotron-3-embed-1b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    check_embedding_ctx_length=False
)

vector_store = Chroma(
    collection_name = "mentors",
    persist_directory= str(DB),
    embedding_function=embeddings
)

with QUESTIONS.open(encoding='utf-8') as file:
    questions = json.load(file)

import time

K = 5
total_recall = 0.0
total_hits = 0

for question in questions:
    expected = set(question['expectedMentorIds'])

    if not expected:
        print(f"\n{question['id']}: no positive mentor IDs; review manually")
        continue

    # Retry loop with backoff for OpenRouter free-tier rate limits (20 req/min)
    results = None
    for attempt in range(4):
        try:
            results = vector_store.similarity_search(question['query'], k=K)
            break
        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e):
                wait_time = (attempt + 1) * 3
                print(f"Rate limited on {question['id']}, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e

    if results is None:
        print(f"Failed to retrieve for {question['id']}")
        continue

    retrieved = [doc.metadata['mentorId'] for doc in results]

    relevant_found = expected.intersection(retrieved)
    recall = len(relevant_found)/len(expected)
    hit = bool(relevant_found)

    total_recall += recall
    total_hits += int(hit)

    print(f'\n{question["id"]}: {question["query"]}')
    print(f"Expected: {sorted(expected)}")
    print(f"Retrieved: {retrieved}")
    print(f"Recall@{K}: {recall:.2f} | Hit: {hit}")

    # Small delay between questions to stay within rate limits
    time.sleep(2)

evaluated = sum(bool(q["expectedMentorIds"]) for q in questions)

if evaluated:
    print(f"\nMean Recall@{K}: {total_recall / evaluated:.2%}")
    print(f"Hit rate@{K}: {total_hits / evaluated:.2%}")


