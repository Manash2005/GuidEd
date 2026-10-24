import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "agent"
DATA_FILE = ROOT / "data" / "mentors.json"
CHROMA_DB = ROOT / "data" / "chroma_db"

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
try:
    from ingestion.loader import load_mentors
except ImportError:
    from agent.ingestion.loader import load_mentors


def get_embeddings():
    """Local dense embedding model BAAI/bge-small-en-v1.5 (runs on CPU via ONNX, 0 API limits)."""
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")


def create_searchable_text(m: dict) -> str:
    """Creates rich, flattened semantic text representation for dense embedding."""
    ai = m.get("aiProfile") or {}
    return (
        f"Mentor Name: {m.get('name')}. "
        f"Domain: {m.get('domain')}. "
        f"Master Sector: {m.get('masterSector')}. "
        f"Sectors of Expertise: {', '.join(m.get('sectorsOfExpertise') or [])}. "
        f"Roles of Expertise: {', '.join(m.get('rolesOfExpertise') or [])}. "
        f"Seniority Level: {m.get('seniority') or 'Unspecified'}. "
        f"Location / City: {m.get('city') or 'Unspecified'}. "
        f"AI Experience: Built AI Product/Workflow: {ai.get('builtAIProductOrWorkflow')}, AI Native: {ai.get('isAINative')}. "
        f"AI Subdomains: {', '.join(ai.get('subdomains') or [])}. "
        f"AI Tools & Automation: {', '.join(ai.get('tools') or [])}."
    )


def extract_metadata(m: dict) -> dict:
    """Extracts categorical metadata for ChromaDB pre-filtering (where clauses)."""
    ai = m.get("aiProfile") or {}
    return {
        "mentorId": str(m.get("mentorId", "")),
        "name": str(m.get("name", "")),
        "city": str(m.get("city") or "").strip().lower(),
        "domain": str(m.get("domain") or "").strip().lower(),
        "masterSector": str(m.get("masterSector") or "").strip().lower(),
        "seniority": str(m.get("seniority") or "").strip().lower(),
        "builtAIProductOrWorkflow": bool(ai.get("builtAIProductOrWorkflow")),
        "isAINative": bool(ai.get("isAINative")),
        "mentorshipQuality": str(m.get("mentorshipQuality") or "").strip().lower(),
        "raw_json": json.dumps(m, ensure_ascii=False)
    }


def index_mentors():
    mentors = load_mentors(DATA_FILE)
    embeddings = get_embeddings()

    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DB))
    try:
        col = client.get_collection("mentors")
        # If dimension mismatch, delete and recreate
        client.delete_collection("mentors")
        print("Reset existing collection for new embedding dimension.")
    except Exception:
        pass

    vector_store = Chroma(
        collection_name="mentors",
        persist_directory=str(CHROMA_DB),
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"}
    )

    documents = [
        Document(
            page_content=create_searchable_text(mentor),
            metadata=extract_metadata(mentor)
        )
        for mentor in mentors
    ]
    ids = [mentor["mentorId"] for mentor in mentors]

    # Clean existing records to avoid duplicates
    try:
        vector_store.delete(ids=ids)
    except Exception:
        pass

    vector_store.add_documents(documents=documents, ids=ids)
    print(f"Indexed {len(documents)} mentors with BGE-small-en-v1.5 and rich metadata.")
    print(f"Total Records in ChromaDB: {vector_store._collection.count()}")


if __name__ == "__main__":
    index_mentors()