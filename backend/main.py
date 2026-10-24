from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from db.mongo import connect_to_mongo, close_mongo_connection
from middleware.security import SecurityHeadersMiddleware, RateLimiterMiddleware
from utils.auth import bootstrap_initial_admin
from routes.mentors_routes import router as mentors_router
from routes.agent_routes import router as agent_router
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.booking_routes import router as booking_router
from routes.student_routes import router as student_router
from routes.mentor_routes import router as mentor_router
from routes.admin_routes import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB & bootstrap admin
    await connect_to_mongo()
    await bootstrap_initial_admin()

    # Ensure ChromaDB vector store is populated
    try:
        from agent.recommender import get_vector_store
        from agent.ingestion.indexer import index_mentors
        vs = get_vector_store()
        count = vs._collection.count()
        if count < 10:
            print(f"ChromaDB has {count} records. Auto-indexing mentors from mentors.json...")
            index_mentors()
            print("ChromaDB auto-indexing completed.")
        else:
            print(f"ChromaDB ready with {count} mentors.")
    except Exception as e:
        print(f"Notice: ChromaDB startup check: {e}")

    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()

app = FastAPI(
    title="Mentor Connect API",
    description="FastAPI Backend for Mentor Connect Career Mentorship Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Exception handlers preventing any sensitive traceback/prompt leaks
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(errors) if errors else "Request validation failed"}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    print(f"Unhandled server exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Security and rate limiting middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)

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
app.include_router(student_router, prefix="/api")
app.include_router(mentor_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Mentor Connect API",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
