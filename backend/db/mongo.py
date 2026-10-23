from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import MONGODB_URI, DATABASE_NAME

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

db_instance = MongoDB()

async def connect_to_mongo():
    if not MONGODB_URI:
        print("Warning: MONGODB_URI not found in environment variables.")
        return
    db_instance.client = AsyncIOMotorClient(MONGODB_URI)
    db_instance.db = db_instance.client[DATABASE_NAME]
    print(f"Connected to MongoDB database: {DATABASE_NAME}")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        print("Closed MongoDB connection.")

def get_database() -> AsyncIOMotorDatabase:
    if db_instance.db is None:
        raise RuntimeError("Database is not initialized. Ensure connect_to_mongo() was called.")
    return db_instance.db
