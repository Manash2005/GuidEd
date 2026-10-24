import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import MONGODB_URI, DATABASE_NAME, DATA_DIR
from utils.auth import hash_password

async def sync_all_mentors():
    if not MONGODB_URI:
        print("MONGODB_URI not set. Skipping sync.")
        return

    client = AsyncIOMotorClient(
        MONGODB_URI,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000
    )
    db = client[DATABASE_NAME]

    mentors_file = DATA_DIR / "mentors.json"
    if not mentors_file.exists():
        print("mentors.json not found.")
        return

    with open(mentors_file, "r", encoding="utf-8") as f:
        mentors = json.load(f)

    now = datetime.now(timezone.utc)
    count = 0

    for m in mentors:
        m_id = m.get("mentorId", "").strip().upper()
        if not m_id:
            continue

        raw_email = m.get("email") or f"mentor.{m_id.lower()}@guided.app"
        email = raw_email.strip().lower().replace("(at)", "@")
        password_plain = f"Mentor@{m_id}!123"
        hashed = hash_password(password_plain)

        user_doc = {
            "userId": f"usr_{m_id.lower()}",
            "email": email,
            "fullName": m.get("name") or f"Mentor {m_id}",
            "role": "mentor",
            "status": "active",
            "mentorId": m_id,
            "targetDomain": m.get("domain"),
            "hashedPassword": hashed,
            "updatedAt": now
        }

        # Check if user with this mentorId or email exists
        existing = await db["users"].find_one({
            "$or": [
                {"mentorId": m_id},
                {"email": email}
            ]
        })

        if existing:
            await db["users"].update_one(
                {"_id": existing["_id"]},
                {"$set": user_doc}
            )
        else:
            user_doc["createdAt"] = now
            await db["users"].insert_one(user_doc)
        count += 1

    print(f"Successfully synced {count} mentors to MongoDB users collection.")
    print("Password formula: Mentor@{mentorId}!123 (e.g., Mentor@M001!123 for M001)")

if __name__ == "__main__":
    asyncio.run(sync_all_mentors())
