import json
import sys
from pathlib import Path
from pymongo import MongoClient, UpdateOne

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import MONGODB_URI, DATABASE_NAME, MENTORS_FILE
from models.mentor_model import MentorBase

def seed():
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI is not set in environment or .env file.")

    if not MENTORS_FILE.exists():
        raise FileNotFoundError(f"Mentors file not found at {MENTORS_FILE}")

    with open(MENTORS_FILE, "r", encoding="utf-8") as f:
        mentors_data = json.load(f)

    if not isinstance(mentors_data, list):
        raise TypeError("mentors.json must contain a JSON array.")

    print(f"Validating {len(mentors_data)} mentors...")
    seen_ids = set()
    validated_mentors = []

    for index, item in enumerate(mentors_data):
        mentor_id = item.get("mentorId")
        name = item.get("name")
        if not mentor_id or not name:
            raise ValueError(f"Mentor at index {index} is missing mentorId or name.")
        if mentor_id in seen_ids:
            raise ValueError(f"Duplicate mentorId found: {mentor_id}")
        seen_ids.add(mentor_id)

        # Validate with Pydantic
        mentor_obj = MentorBase(**item)
        validated_mentors.append(mentor_obj.model_dump())

    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db["mentors"]

    # Ensure unique index on mentorId
    collection.create_index("mentorId", unique=True)

    # Bulk upsert
    operations = [
        UpdateOne(
            {"mentorId": m["mentorId"]},
            {"$set": m},
            upsert=True
        )
        for m in validated_mentors
    ]

    result = collection.bulk_write(operations)
    print(f"Successfully processed {len(validated_mentors)} mentors:")
    print(f" - Upserted: {len(result.upserted_ids)}")
    print(f" - Modified: {result.modified_count}")
    print(f" - Matched:  {result.matched_count}")

    client.close()

if __name__ == "__main__":
    seed()
