from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, db_manager
from app.seed import seed_database
from app.routers import (
    auth_router,
    students_router,
    attendance_router,
    news_router,
    web_content_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for MongoDB connection and automatic seeding."""
    print("[CFSI Backend] Starting up FastAPI with MongoDB...")
    await connect_to_mongo()
    await seed_database()
    yield
    print("[CFSI Backend] Shutting down...")
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Central Fire Safety Institute (CFSI) Enterprise API with MongoDB & JWT Authentication",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in settings.CORS_ORIGINS if origin != "*"],  # Allows all origins for easy development and network testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(attendance_router)
app.include_router(news_router)
app.include_router(web_content_router)

@app.get("/")
def root():
    return {
        "institute": "Central Fire Safety Institute (CFSI), Vadodara",
        "api": "CFSI REST API",
        "database": "MongoDB",
        "mode": "live" if not db_manager.is_mock else "in-memory (mongomock)",
        "docs": "/docs",
        "version": settings.VERSION
    }

@app.get("/api/health")
def healthcheck():
    return {
        "status": "healthy",
        "database": "mongodb",
        "is_mock": db_manager.is_mock,
        "message": "Connected to MongoDB" if not db_manager.is_mock else "Running on mongomock development engine"
    }

from app.routers.users import router as users_router
app.include_router(users_router)
