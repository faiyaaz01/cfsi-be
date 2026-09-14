import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from starlette.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.attendance import (
    AttendanceOut, AttendanceCreate, AttendanceUpdate, AttendanceBulkCreate
)
from app.dependencies import get_current_user, require_staff

router = APIRouter(prefix="/api/attendance", tags=["Attendance Muster"])

class AttendanceBroadcaster:
    """In-memory pub/sub broadcaster for real-time Server-Sent Events (SSE)."""
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast(self, event_data: dict):
        for q in list(self._subscribers):
            try:
                await q.put(event_data)
            except Exception:
                pass

broadcaster = AttendanceBroadcaster()

def compute_lock_status(doc: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Computes whether an attendance record is locked based on the 24-hour editing window.
    Returns (is_locked, uploaded_at_iso, can_edit_until_iso).
    """
    raw_uploaded = doc.get("uploaded_at") or doc.get("uploadedAt") or doc.get("created_at") or doc.get("createdAt")
    if not raw_uploaded:
        return False, None, None
    try:
        clean_str = str(raw_uploaded)
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        deadline = dt + timedelta(hours=24)
        now = datetime.now(timezone.utc)
        is_locked = now > deadline
        return is_locked, dt.isoformat(), deadline.isoformat()
    except Exception:
        return False, str(raw_uploaded), None

def doc_to_attendance_out(doc: Dict[str, Any]) -> AttendanceOut:
    is_locked, uploaded_at, can_edit_until = compute_lock_status(doc)
    return AttendanceOut(
        id=str(doc.get("id") or doc.get("_id") or ""),
        student_id=doc.get("student_id") or doc.get("studentId") or doc.get("id") or "",
        roll_no=doc.get("roll_no") or doc.get("rollNo"),
        date=doc.get("date", ""),
        slot=doc.get("slot", ""),
        course=doc.get("course", ""),
        status=doc.get("status", "Present"),
        topic_or_module=doc.get("topic_or_module") or doc.get("topicOrModule"),
        remarks=doc.get("remarks"),
        marked_by=doc.get("marked_by") or doc.get("markedBy"),
        created_at=doc.get("created_at") or doc.get("createdAt"),
        uploaded_at=uploaded_at,
        is_locked=is_locked,
        can_edit_until=can_edit_until
    )

@router.get("/stream")
async def attendance_stream(request: Request):
    """
    Real-time Server-Sent Events (SSE) stream for attendance muster updates.
    Broadcasts events to active clients (Admin, Teacher, Student) immediately.
    """
    async def event_generator():
        q = await broadcaster.subscribe()
        try:
            yield "data: {\"event\": \"connected\"}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("", response_model=List[AttendanceOut], response_model_by_alias=True)
async def get_attendance(
    date: Optional[str] = None,
    slot: Optional[str] = None,
    student_id: Optional[str] = None,
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Query attendance records from MongoDB.
    - If student is logged in, restricted to their own student ID or roll no.
    - If admin or staff is logged in, can view all records and filter by date, slot, student_id, course.
    """
    filter_q = {}

    if current_user.get("role") == "student":
        sid = current_user.get("student_id") or current_user.get("username")
        if not sid:
            return []
        filter_q["$or"] = [{"student_id": sid}, {"roll_no": sid}]
    elif student_id:
        filter_q["$or"] = [{"student_id": student_id}, {"roll_no": student_id}]

    if date:
        filter_q["date"] = date
    if slot:
        filter_q["slot"] = slot
    if course:
        filter_q["course"] = course

    cursor = db.attendance.find(filter_q).sort([("date", -1), ("slot", 1)])
    records = []
    async for doc in cursor:
        records.append(doc_to_attendance_out(doc))
    return records

@router.post("", response_model=AttendanceOut, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
async def create_or_upsert_attendance(
    record: AttendanceCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Mark attendance for a cadet in a slot with upsert and 24-hour lock check."""
    query = {
        "student_id": record.student_id,
        "date": record.date,
        "slot": record.slot
    }
    
    existing = await db.attendance.find_one(query)
    if existing:
        is_locked, _, can_edit_until = compute_lock_status(existing)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Attendance record is locked: cannot be modified after 24 hours of upload (expired at {can_edit_until})."
            )

    now_iso = datetime.now(timezone.utc).isoformat()
    new_id = record.id or (existing.get("id") if existing else None) or f"att-{uuid.uuid4().hex[:8]}"
    created_at = (existing.get("created_at") if existing else None) or record.created_at or now_iso
    uploaded_at = (existing.get("uploaded_at") if existing else None) or record.uploaded_at or now_iso
    marked_by = record.marked_by or current_user.get("full_name") or current_user.get("username")

    update_fields = {
        "student_id": record.student_id,
        "roll_no": record.roll_no,
        "course": record.course,
        "status": record.status,
        "topic_or_module": record.topic_or_module,
        "remarks": record.remarks,
        "marked_by": marked_by,
        "uploaded_at": uploaded_at
    }

    doc = await db.attendance.find_one_and_update(
        query,
        {
            "$set": update_fields,
            "$setOnInsert": {
                "_id": new_id,
                "id": new_id,
                "date": record.date,
                "slot": record.slot,
                "created_at": created_at
            }
        },
        upsert=True,
        return_document=True
    )
    result = doc_to_attendance_out(doc)

    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "upsert",
        "date": record.date,
        "student_id": record.student_id,
        "slot": record.slot,
        "timestamp": now_iso
    })

    return result

@router.post("/bulk", response_model=List[AttendanceOut], response_model_by_alias=True)
async def bulk_save_attendance(
    payload: AttendanceBulkCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """
    Bulk upsert 3-slot muster table attendance records in MongoDB (Admin/Teacher only).
    Enforces 24-hour locking window and broadcasts real-time updates.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    default_marker = current_user.get("full_name") or current_user.get("username")

    # Pre-validation: check if any record being touched is already locked
    for item in payload.records:
        query = {
            "student_id": item.student_id,
            "date": item.date,
            "slot": item.slot
        }
        existing = await db.attendance.find_one(query)
        if existing:
            is_locked, _, can_edit_until = compute_lock_status(existing)
            if is_locked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Attendance for date '{item.date}' is locked: the 24-hour editing window expired at {can_edit_until}."
                )

    saved_records = []
    affected_dates = set()

    for item in payload.records:
        query = {
            "student_id": item.student_id,
            "date": item.date,
            "slot": item.slot
        }
        existing = await db.attendance.find_one(query)
        uploaded_at = (existing.get("uploaded_at") if existing else None) or item.uploaded_at or now_iso
        created_at = (existing.get("created_at") if existing else None) or item.created_at or now_iso
        item_id = item.id or (existing.get("id") if existing else None) or f"att-{uuid.uuid4().hex[:8]}"

        doc = await db.attendance.find_one_and_update(
            query,
            {
                "$set": {
                    "student_id": item.student_id,
                    "roll_no": item.roll_no,
                    "date": item.date,
                    "slot": item.slot,
                    "course": item.course,
                    "status": item.status,
                    "topic_or_module": item.topic_or_module,
                    "remarks": item.remarks,
                    "marked_by": item.marked_by or default_marker,
                    "uploaded_at": uploaded_at
                },
                "$setOnInsert": {
                    "_id": item_id,
                    "id": item_id,
                    "created_at": created_at
                }
            },
            upsert=True,
            return_document=True
        )
        saved_records.append(doc_to_attendance_out(doc))
        affected_dates.add(item.date)

    # Broadcast real-time update to all active clients (students, teachers, admins)
    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "bulk_upload",
        "dates": list(affected_dates),
        "count": len(saved_records),
        "timestamp": now_iso
    })

    return saved_records

@router.put("/{record_id}", response_model=AttendanceOut, response_model_by_alias=True)
async def update_attendance(
    record_id: str,
    update_data: AttendanceUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Update a specific attendance record by ID (restricted to 24 hours)."""
    existing = await db.attendance.find_one({"$or": [{"_id": record_id}, {"id": record_id}]})
    if not existing:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    is_locked, _, can_edit_until = compute_lock_status(existing)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance record is locked: cannot be modified after 24 hours of upload (expired at {can_edit_until})."
        )

    update_fields = {}
    if update_data.status is not None:
        update_fields["status"] = update_data.status
    if update_data.topic_or_module is not None:
        update_fields["topic_or_module"] = update_data.topic_or_module
    if update_data.remarks is not None:
        update_fields["remarks"] = update_data.remarks
    if update_data.marked_by is not None:
        update_fields["marked_by"] = update_data.marked_by

    doc = await db.attendance.find_one_and_update(
        {"_id": existing["_id"]},
        {"$set": update_fields},
        return_document=True
    )
    result = doc_to_attendance_out(doc)

    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "update",
        "record_id": record_id,
        "date": doc.get("date"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return result

@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    record_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Delete attendance record by ID (restricted to 24 hours)."""
    existing = await db.attendance.find_one({"$or": [{"_id": record_id}, {"id": record_id}]})
    if not existing:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    is_locked, _, can_edit_until = compute_lock_status(existing)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance record is locked: cannot be deleted after 24 hours of upload (expired at {can_edit_until})."
        )

    await db.attendance.delete_one({"_id": existing["_id"]})

    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "delete",
        "record_id": record_id,
        "date": existing.get("date"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return None

@router.delete("/day/{date}", status_code=status.HTTP_200_OK)
async def clear_day_attendance(
    date: str,
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Reset attendance records for a specific date (restricted to 24 hours)."""
    filter_q = {"date": date}
    if course:
        filter_q["course"] = course

    cursor = db.attendance.find(filter_q)
    async for doc in cursor:
        is_locked, _, can_edit_until = compute_lock_status(doc)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Attendance for date '{date}' is locked: cannot be cleared after 24 hours of upload (expired at {can_edit_until})."
            )

    res = await db.attendance.delete_many(filter_q)

    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "clear_day",
        "date": date,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"deleted": res.deleted_count, "date": date}

@router.delete("", status_code=status.HTTP_200_OK)
async def clear_all_attendance(
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """
    Clear all attendance muster records or for an optional course in MongoDB (Admin/Staff only).
    Used for database reset and testing.
    """
    filter_q = {}
    if course:
        filter_q["course"] = course
    res = await db.attendance.delete_many(filter_q)

    await broadcaster.broadcast({
        "event": "attendance_updated",
        "action": "clear_all",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return {"deleted": res.deleted_count}

