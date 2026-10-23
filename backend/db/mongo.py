import certifi
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
    try:
        db_instance.client = AsyncIOMotorClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=3000
        )
        db_instance.db = db_instance.client[DATABASE_NAME]
        print(f"Initialized MongoDB client for database: {DATABASE_NAME}")
    except Exception as e:
        print(f"Warning: Failed to connect to MongoDB: {e}")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        print("Closed MongoDB connection.")

def get_database() -> Optional[AsyncIOMotorDatabase]:
    return db_instance.db
