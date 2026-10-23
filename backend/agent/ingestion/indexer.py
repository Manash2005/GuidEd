import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "agent"
DATA_FILE = ROOT / "data" / "mentors.json"
CHROMA_DB = ROOT / "data" / "chroma_db"

# Ensure environment variables are loaded from backend/.env
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
try:
    from ingestion.loader import load_mentors
except ImportError:
    from agent.ingestion.loader import load_mentors


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("API key not found")

    mentors = load_mentors(DATA_FILE)

    embeddings = OpenAIEmbeddings(
        model="nvidia/nemotron-3-embed-1b:free",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        check_embedding_ctx_length=False
    )

    vector_store = Chroma(
        collection_name="mentors",
        persist_directory=str(CHROMA_DB),
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"}
    )

    documents = [
        Document(
            page_content=json.dumps(mentor, ensure_ascii=False),
            metadata={"mentorId": mentor["mentorId"]}
        )
        for mentor in mentors
    ]
    ids = [mentor["mentorId"] for mentor in mentors]

    vector_store.add_documents(
        documents=documents,
        ids=ids
    )

    print(f"Indexed {len(documents)} mentors")
    print(f"Total Records : {vector_store._collection.count()}")


if __name__ == "__main__":
    main()