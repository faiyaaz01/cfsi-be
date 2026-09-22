from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, db_manager, get_database
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
    allow_origins=[origin for origin in settings.CORS_ORIGINS if origin != "*"],
    allow_origin_regex=r"^https?://.*",
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

# Dynamic Media Serving Route (Local disk + MongoDB fallback for Vercel/serverless)
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
try:
    uploads_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    uploads_dir = Path("/tmp/uploads")
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

@app.get("/api/uploads/{filename}")
@app.get("/uploads/{filename}")
async def serve_uploaded_media(filename: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    # 1. Check local disk first (instant on localhost/VPS)
    disk_path = uploads_dir / filename
    if disk_path.exists() and disk_path.is_file():
        return FileResponse(str(disk_path))

    # 2. Check MongoDB media_files (persistent on Vercel / serverless)
    doc = await db.media_files.find_one({"_id": filename})
    if doc and "data" in doc:
        return Response(
            content=doc["data"],
            media_type=doc.get("content_type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=31536000, immutable"}
        )

    raise HTTPException(status_code=404, detail="Image not found")

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
