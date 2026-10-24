from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from db.mongo import connect_to_mongo, close_mongo_connection
from routes.mentors_routes import router as mentors_router
from routes.agent_routes import router as agent_router
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.booking_routes import router as booking_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()

app = FastAPI(
    title="GuidEd API",
    description="FastAPI Backend for GuidEd Mentorship & AI Agent Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/api")
app.include_router(mentors_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(booking_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to GuidEd API",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
