from typing import List, Dict, Any, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.dependencies import require_admin
from app.schemas.web_content import (
    CourseOut, CourseCreate, CourseUpdate,
    TrainingDrillOut, TrainingDrillCreate, TrainingDrillUpdate,
    GalleryPhotoOut, GalleryPhotoCreate, GalleryPhotoUpdate,
    GalleryVideoOut, GalleryVideoCreate, GalleryVideoUpdate,
    DisplaySettingsSchema, HomePageConfigSchema,
    ReorderRequest
)

router = APIRouter(prefix="/api/web", tags=["Web & Content Management"])

def set_edge_cache(response: Response, s_maxage: int = 120, swr: int = 300):
    """Adds CDN Edge caching headers for high-speed delivery via Vercel Edge Network."""
    response.headers["Cache-Control"] = f"public, max-age=60, s-maxage={s_maxage}, stale-while-revalidate={swr}"

# =========================================================================
# 1. COURSES ENDPOINTS
# =========================================================================
def doc_to_course_out(doc: Dict[str, Any]) -> CourseOut:
    return CourseOut(
        id=str(doc.get("id") or doc.get("_id")),
        title=doc.get("title", ""),
        slug=doc.get("slug", ""),
        duration=doc.get("duration", ""),
        eligibility=doc.get("eligibility", ""),
        fee=doc.get("fee", ""),
        feeNumber=doc.get("fee_number", doc.get("feeNumber", 0)),
        badge=doc.get("badge"),
        icon=doc.get("icon", "Flame"),
        shortDescription=doc.get("short_description", doc.get("shortDescription", "")),
        fullDescription=doc.get("full_description", doc.get("fullDescription", "")),
        syllabus=doc.get("syllabus", []),
        physicalRequirements=doc.get("physical_requirements", doc.get("physicalRequirements", [])),
        careerOpportunities=doc.get("career_opportunities", doc.get("careerOpportunities", [])),
        certificationBody=doc.get("certification_body", doc.get("certificationBody", "")),
        order=doc.get("order", 0)
    )

@router.get("/courses", response_model=List[CourseOut])
async def get_courses(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    cursor = db.courses.find().sort([("order", 1), ("title", 1)])
    courses = []
    async for doc in cursor:
        courses.append(doc_to_course_out(doc))
    return courses

@router.put("/courses/reorder", status_code=status.HTTP_200_OK)
async def reorder_courses(
    reorder_in: ReorderRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint to reorder courses manually."""
    if reorder_in.ids:
        for idx, c_id in enumerate(reorder_in.ids):
            await db.courses.update_one(
                {"$or": [{"_id": c_id}, {"id": c_id}]},
                {"$set": {"order": idx}}
            )
    elif reorder_in.items:
        for item in reorder_in.items:
            await db.courses.update_one(
                {"$or": [{"_id": item.id}, {"id": item.id}]},
                {"$set": {"order": item.order}}
            )
    return {"status": "success", "message": "Courses reordered successfully"}

@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    course_id = course_in.id or f"cfs-{uuid.uuid4().hex[:8]}"
    curr_count = await db.courses.count_documents({})
    order_val = course_in.order if (course_in.order is not None and course_in.order != 0) else curr_count
    doc = {
        "_id": course_id,
        "id": course_id,
        "title": course_in.title,
        "slug": course_in.slug,
        "duration": course_in.duration,
        "eligibility": course_in.eligibility,
        "fee": course_in.fee,
        "fee_number": course_in.fee_number,
        "badge": course_in.badge,
        "icon": course_in.icon,
        "short_description": course_in.short_description,
        "full_description": course_in.full_description,
        "syllabus": course_in.syllabus,
        "physical_requirements": course_in.physical_requirements,
        "career_opportunities": course_in.career_opportunities,
        "certification_body": course_in.certification_body,
        "order": order_val
    }
    await db.courses.insert_one(doc)
    return doc_to_course_out(doc)

@router.put("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: str,
    course_in: CourseUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    update_data = {k: v for k, v in course_in.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    doc = await db.courses.find_one_and_update(
        {"$or": [{"_id": course_id}, {"id": course_id}]},
        {"$set": update_data},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    return doc_to_course_out(doc)

@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.courses.delete_one({"$or": [{"_id": course_id}, {"id": course_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return None

@router.delete("/courses", status_code=status.HTTP_200_OK)
async def clear_all_courses(
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.courses.delete_many({})
    return {"message": "All courses cleared successfully", "deleted": res.deleted_count}

# =========================================================================
# 2. TRAINING DRILLS ENDPOINTS
# =========================================================================
def doc_to_drill_out(doc: Dict[str, Any]) -> TrainingDrillOut:
    return TrainingDrillOut(
        id=str(doc.get("id") or doc.get("_id")),
        title=doc.get("title", ""),
        tag=doc.get("tag", "Drill"),
        duration=doc.get("duration", "Practical"),
        image=doc.get("image", ""),
        description=doc.get("description", ""),
        highlights=doc.get("highlights", []),
        equipmentUsed=doc.get("equipment_used", doc.get("equipmentUsed", [])),
        order=doc.get("order", 0)
    )

@router.get("/drills", response_model=List[TrainingDrillOut])
async def get_drills(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    cursor = db.training_drills.find().sort([("order", 1), ("title", 1)])
    drills = []
    async for doc in cursor:
        drills.append(doc_to_drill_out(doc))
    return drills

@router.put("/drills/reorder", status_code=status.HTTP_200_OK)
async def reorder_drills(
    reorder_in: ReorderRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint to reorder training drills manually."""
    if reorder_in.ids:
        for idx, d_id in enumerate(reorder_in.ids):
            await db.training_drills.update_one(
                {"$or": [{"_id": d_id}, {"id": d_id}]},
                {"$set": {"order": idx}}
            )
    elif reorder_in.items:
        for item in reorder_in.items:
            await db.training_drills.update_one(
                {"$or": [{"_id": item.id}, {"id": item.id}]},
                {"$set": {"order": item.order}}
            )
    return {"status": "success", "message": "Training drills reordered successfully"}

@router.post("/drills", response_model=TrainingDrillOut, status_code=status.HTTP_201_CREATED)
async def create_drill(
    drill_in: TrainingDrillCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    drill_id = drill_in.id or f"tr-{uuid.uuid4().hex[:8]}"
    curr_count = await db.training_drills.count_documents({})
    order_val = drill_in.order if (drill_in.order is not None and drill_in.order != 0) else curr_count
    doc = {
        "_id": drill_id,
        "id": drill_id,
        "title": drill_in.title,
        "tag": drill_in.tag,
        "duration": drill_in.duration,
        "image": drill_in.image,
        "description": drill_in.description,
        "highlights": drill_in.highlights,
        "equipment_used": drill_in.equipment_used,
        "order": order_val
    }
    await db.training_drills.insert_one(doc)
    return doc_to_drill_out(doc)

@router.put("/drills/{drill_id}", response_model=TrainingDrillOut)
async def update_drill(
    drill_id: str,
    drill_in: TrainingDrillUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    update_data = {k: v for k, v in drill_in.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    doc = await db.training_drills.find_one_and_update(
        {"$or": [{"_id": drill_id}, {"id": drill_id}]},
        {"$set": update_data},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Training drill not found")
    return doc_to_drill_out(doc)

@router.delete("/drills/{drill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drill(
    drill_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.training_drills.delete_one({"$or": [{"_id": drill_id}, {"id": drill_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Training drill not found")
    return None

@router.delete("/drills", status_code=status.HTTP_200_OK)
async def clear_all_drills(
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.training_drills.delete_many({})
    return {"message": "All ground drills cleared successfully", "deleted": res.deleted_count}

# =========================================================================
# 3. PHOTO GALLERY ENDPOINTS
# =========================================================================
def doc_to_photo_out(doc: Dict[str, Any]) -> GalleryPhotoOut:
    return GalleryPhotoOut(
        id=str(doc.get("id") or doc.get("_id")),
        title=doc.get("title", ""),
        category=doc.get("category", "Training"),
        imageUrl=doc.get("image_url", doc.get("imageUrl", "")),
        caption=doc.get("caption", ""),
        date=doc.get("date", ""),
        order=doc.get("order", 0)
    )

@router.get("/photos", response_model=List[GalleryPhotoOut])
async def get_photos(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    cursor = db.gallery_photos.find().sort([("order", 1), ("date", -1)])
    photos = []
    async for doc in cursor:
        photos.append(doc_to_photo_out(doc))
    return photos

@router.put("/photos/reorder", status_code=status.HTTP_200_OK)
async def reorder_photos(
    reorder_in: ReorderRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint to reorder gallery photos manually."""
    if reorder_in.ids:
        for idx, p_id in enumerate(reorder_in.ids):
            await db.gallery_photos.update_one(
                {"$or": [{"_id": p_id}, {"id": p_id}]},
                {"$set": {"order": idx}}
            )
    elif reorder_in.items:
        for item in reorder_in.items:
            await db.gallery_photos.update_one(
                {"$or": [{"_id": item.id}, {"id": item.id}]},
                {"$set": {"order": item.order}}
            )
    return {"status": "success", "message": "Gallery photos reordered successfully"}

@router.post("/photos", response_model=GalleryPhotoOut, status_code=status.HTTP_201_CREATED)
async def create_photo(
    photo_in: GalleryPhotoCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    photo_id = photo_in.id or f"img-{uuid.uuid4().hex[:8]}"
    curr_count = await db.gallery_photos.count_documents({})
    order_val = photo_in.order if (photo_in.order is not None and photo_in.order != 0) else curr_count
    doc = {
        "_id": photo_id,
        "id": photo_id,
        "title": photo_in.title,
        "category": photo_in.category,
        "image_url": photo_in.image_url,
        "caption": photo_in.caption,
        "date": photo_in.date,
        "order": order_val
    }
    await db.gallery_photos.insert_one(doc)
    return doc_to_photo_out(doc)

@router.put("/photos/{photo_id}", response_model=GalleryPhotoOut)
async def update_photo(
    photo_id: str,
    photo_in: GalleryPhotoUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    update_data = {k: v for k, v in photo_in.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    doc = await db.gallery_photos.find_one_and_update(
        {"$or": [{"_id": photo_id}, {"id": photo_id}]},
        {"$set": update_data},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")
    return doc_to_photo_out(doc)

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.gallery_photos.delete_one({"$or": [{"_id": photo_id}, {"id": photo_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    return None

@router.delete("/photos", status_code=status.HTTP_200_OK)
async def clear_all_photos(
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.gallery_photos.delete_many({})
    return {"message": "All photos cleared successfully", "deleted": res.deleted_count}

# =========================================================================
# 4. VIDEO GALLERY ENDPOINTS
# =========================================================================
def doc_to_video_out(doc: Dict[str, Any]) -> GalleryVideoOut:
    return GalleryVideoOut(
        id=str(doc.get("id") or doc.get("_id")),
        youtubeId=doc.get("youtube_id", doc.get("youtubeId", "")),
        title=doc.get("title", ""),
        category=doc.get("category", "Practical Drill"),
        duration=doc.get("duration", "3:00"),
        description=doc.get("description", ""),
        order=doc.get("order", 0)
    )

@router.get("/videos", response_model=List[GalleryVideoOut])
async def get_videos(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    cursor = db.gallery_videos.find().sort([("order", 1), ("title", 1)])
    videos = []
    async for doc in cursor:
        videos.append(doc_to_video_out(doc))
    return videos

@router.put("/videos/reorder", status_code=status.HTTP_200_OK)
async def reorder_videos(
    reorder_in: ReorderRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint to reorder gallery videos manually."""
    if reorder_in.ids:
        for idx, v_id in enumerate(reorder_in.ids):
            await db.gallery_videos.update_one(
                {"$or": [{"_id": v_id}, {"id": v_id}]},
                {"$set": {"order": idx}}
            )
    elif reorder_in.items:
        for item in reorder_in.items:
            await db.gallery_videos.update_one(
                {"$or": [{"_id": item.id}, {"id": item.id}]},
                {"$set": {"order": item.order}}
            )
    return {"status": "success", "message": "Gallery videos reordered successfully"}

@router.post("/videos", response_model=GalleryVideoOut, status_code=status.HTTP_201_CREATED)
async def create_video(
    video_in: GalleryVideoCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    video_id = video_in.id or f"vid-{uuid.uuid4().hex[:8]}"
    curr_count = await db.gallery_videos.count_documents({})
    order_val = video_in.order if (video_in.order is not None and video_in.order != 0) else curr_count
    doc = {
        "_id": video_id,
        "id": video_id,
        "youtube_id": video_in.youtube_id,
        "title": video_in.title,
        "category": video_in.category,
        "duration": video_in.duration,
        "description": video_in.description,
        "order": order_val
    }
    await db.gallery_videos.insert_one(doc)
    return doc_to_video_out(doc)

@router.put("/videos/{video_id}", response_model=GalleryVideoOut)
async def update_video(
    video_id: str,
    video_in: GalleryVideoUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    update_data = {k: v for k, v in video_in.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    
    doc = await db.gallery_videos.find_one_and_update(
        {"$or": [{"_id": video_id}, {"id": video_id}]},
        {"$set": update_data},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")
    return doc_to_video_out(doc)

@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.gallery_videos.delete_one({"$or": [{"_id": video_id}, {"id": video_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return None

@router.delete("/videos", status_code=status.HTTP_200_OK)
async def clear_all_videos(
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    res = await db.gallery_videos.delete_many({})
    return {"message": "All videos cleared successfully", "deleted": res.deleted_count}

# =========================================================================
# 5. DISPLAY & VISIBILITY SETTINGS ENDPOINTS
# =========================================================================
@router.get("/display-settings", response_model=DisplaySettingsSchema)
async def get_display_settings(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    doc = await db.display_settings.find_one({"_id": "global_display_settings"})
    if not doc:
        default_settings = DisplaySettingsSchema()
        return default_settings
    return DisplaySettingsSchema(**{k: v for k, v in doc.items() if k != "_id"})

@router.put("/display-settings", response_model=DisplaySettingsSchema)
async def update_display_settings(
    settings_in: DisplaySettingsSchema,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    doc_data = settings_in.model_dump()
    await db.display_settings.update_one(
        {"_id": "global_display_settings"},
        {"$set": doc_data},
        upsert=True
    )
    return settings_in

# =========================================================================
# 6. HOMEPAGE CONFIGURATION ENDPOINTS
# =========================================================================
@router.get("/homepage-config", response_model=HomePageConfigSchema)
async def get_homepage_config(response: Response, db: AsyncIOMotorDatabase = Depends(get_database)):
    set_edge_cache(response)
    doc = await db.homepage_config.find_one({"_id": "global_homepage_config"})
    if not doc:
        return HomePageConfigSchema()
    return HomePageConfigSchema(**{k: v for k, v in doc.items() if k != "_id"})

@router.put("/homepage-config", response_model=HomePageConfigSchema)
async def update_homepage_config(
    config_in: HomePageConfigSchema,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: Dict[str, Any] = Depends(require_admin)
):
    doc_data = config_in.model_dump()
    await db.homepage_config.update_one(
        {"_id": "global_homepage_config"},
        {"$set": doc_data},
        upsert=True
    )
    return config_in

