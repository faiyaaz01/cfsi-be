from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.news import NewsOut, NewsCreate, NewsUpdate
from app.dependencies import require_admin

router = APIRouter(prefix="/api/news", tags=["News & Bulletins"])

def doc_to_news_out(doc: Dict[str, Any]) -> NewsOut:
    return NewsOut(
        id=str(doc.get("id") or doc.get("_id")),
        title=doc["title"],
        category=doc["category"],
        date=doc["date"],
        excerpt=doc["excerpt"],
        content=doc["content"],
        image_url=doc.get("image_url"),
        author=doc["author"],
        is_pinned=bool(doc.get("is_pinned", False)),
        created_at=doc.get("created_at")
    )

@router.get("", response_model=List[NewsOut])
async def get_all_news(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Fetch all institute news bulletins and circulars from MongoDB."""
    cursor = db.news_posts.find().sort([("is_pinned", -1), ("date", -1)])
    posts = []
    async for doc in cursor:
        posts.append(doc_to_news_out(doc))
    return posts

@router.get("/{news_id}", response_model=NewsOut)
async def get_news_detail(news_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Fetch single news item by ID from MongoDB."""
    doc = await db.news_posts.find_one({"$or": [{"_id": news_id}, {"id": news_id}]})
    if not doc:
        raise HTTPException(status_code=404, detail="News post not found")
    return doc_to_news_out(doc)

@router.post("", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
async def create_news(
    news_in: NewsCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Publish a new institute announcement in MongoDB (Admin only)."""
    new_id = news_in.id or f"news-{uuid.uuid4().hex[:8]}"
    created_at = news_in.created_at or datetime.now(timezone.utc).isoformat()
    
    doc = {
        "_id": new_id,
        "id": new_id,
        "title": news_in.title,
        "category": news_in.category,
        "date": news_in.date,
        "excerpt": news_in.excerpt,
        "content": news_in.content,
        "image_url": news_in.image_url,
        "author": news_in.author,
        "is_pinned": news_in.is_pinned,
        "created_at": created_at
    }
    await db.news_posts.insert_one(doc)
    return doc_to_news_out(doc)

@router.put("/{news_id}", response_model=NewsOut)
async def update_news(
    news_id: str,
    news_update: NewsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Update news article in MongoDB (Admin only)."""
    update_fields = {}
    if news_update.title is not None:
        update_fields["title"] = news_update.title
    if news_update.category is not None:
        update_fields["category"] = news_update.category
    if news_update.date is not None:
        update_fields["date"] = news_update.date
    if news_update.excerpt is not None:
        update_fields["excerpt"] = news_update.excerpt
    if news_update.content is not None:
        update_fields["content"] = news_update.content
    if news_update.image_url is not None:
        update_fields["image_url"] = news_update.image_url
    if news_update.author is not None:
        update_fields["author"] = news_update.author
    if news_update.is_pinned is not None:
        update_fields["is_pinned"] = news_update.is_pinned

    doc = await db.news_posts.find_one_and_update(
        {"$or": [{"_id": news_id}, {"id": news_id}]},
        {"$set": update_fields},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="News post not found")
    return doc_to_news_out(doc)

@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Delete a news announcement from MongoDB (Admin only)."""
    res = await db.news_posts.delete_one({"$or": [{"_id": news_id}, {"id": news_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="News post not found")
    return None
