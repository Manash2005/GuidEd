import os
from dotenv import load_dotenv
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_chroma import Chroma
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "chroma_db"
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

vector_store = Chroma(
    collection_name="mentors",
    persist_directory=str(DB_PATH),
    embedding_function=embeddings
)

query = "I'm a software professional interested in moving into AI product management. Which mentors are relevant?"

results = vector_store.similarity_search_with_score(query, k=5)

for document, distance in results:
    print(f"\nMentor Id : {document.metadata['mentorId']}")
    print(f"Distance: {distance:.4f}")
    print(document.page_content)