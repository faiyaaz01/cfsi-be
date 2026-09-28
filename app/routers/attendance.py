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
from pymongo import UpdateOne
from app.dependencies import get_current_user, require_staff, require_admin

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

def get_ist_now() -> datetime:
    """Returns the current datetime in Indian Standard Time (UTC+5:30)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz)

def compute_slot1_start_and_deadline_ist(date_str: str) -> tuple[datetime, datetime]:
    """
    Given a date string 'YYYY-MM-DD', returns (slot1_start_ist, lock_deadline_ist).
    - Slot 1 start time is 08:00:00 AM IST on date_str.
    - Lock deadline is strictly 48 hours from Slot 1 start (08:00 AM IST on date_str + 2 days).
    """
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    parts = [int(p) for p in str(date_str).strip().split("-")]
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {date_str}")
    slot1_start = datetime(parts[0], parts[1], parts[2], 8, 0, 0, tzinfo=ist_tz)
    lock_deadline = slot1_start + timedelta(hours=48)
    return slot1_start, lock_deadline

def compute_lock_status(doc: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Computes whether an attendance record is locked based on the 48-hour editing window.
    Returns (is_locked, uploaded_at_iso, can_edit_until_iso).
    """
    raw_uploaded = doc.get("uploaded_at") or doc.get("uploadedAt") or doc.get("created_at") or doc.get("createdAt")
    can_edit_until = doc.get("can_edit_until") or doc.get("canEditUntil")
    doc_date = doc.get("date")

    # If explicitly set by admin unlock/lock
    if "is_locked" in doc and doc["is_locked"] is not None:
        return bool(doc["is_locked"]), str(raw_uploaded) if raw_uploaded else None, str(can_edit_until) if can_edit_until else None

    # Priority 1: Check date-based 48-hour window from Slot 1 (08:00 AM IST)
    if doc_date:
        try:
            slot1_start, deadline_ist = compute_slot1_start_and_deadline_ist(doc_date)
            now_ist = get_ist_now()
            # If past 48h deadline or before Slot 1 start
            is_locked = now_ist > deadline_ist or now_ist < slot1_start
            return is_locked, str(raw_uploaded) if raw_uploaded else slot1_start.isoformat(), deadline_ist.isoformat()
        except Exception:
            pass

    # Priority 2: Fallback to uploaded timestamp + 48 hours
    if not raw_uploaded:
        return False, None, None
    try:
        clean_str = str(raw_uploaded)
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        deadline = dt + timedelta(hours=48)
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

def check_leader_slot_lock(slot: str, date_str: str, current_user: Dict[str, Any]):
    """
    Validates slot-wise time lock for users with role 'leader'.
    Leaders can only mark attendance:
    1. For today's date in Indian Standard Time (IST)
    2. During the slot's active window:
       - Slot 1: 08:00 to 10:20 AM (Locked at 10:20 AM)
       - Slot 2: 10:30 AM to 01:20 PM / 13:20 (Locked at 01:20 PM)
       - Slot 3: 02:00 PM / 14:00 to 05:20 PM / 17:20 (Locked at 05:20 PM)
    Admins and teachers bypass this rule.
    """
    if current_user.get("role") != "leader":
        return

    # Check assigned slots if specified on user profile
    assigned_slots = current_user.get("assigned_slots") or []
    if assigned_slots and slot not in assigned_slots:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You are not assigned to mark attendance for {slot}."
        )

    # Calculate IST time (UTC+5:30)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)
    today_str = now_ist.strftime("%Y-%m-%d")

    if date_str != today_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Leaders can only mark attendance for today ({today_str}). Past or future dates are locked."
        )

    norm_slot = (slot or "").strip().lower()
    current_minutes = now_ist.hour * 60 + now_ist.minute

    # Windows in minutes from midnight:
    # Slot 1: 08:00 (480) to 10:20 (620)
    # Slot 2: 10:30 (630) to 13:20 (800)
    # Slot 3: 14:00 (840) to 17:20 (1040)
    if "1" in norm_slot or "one" in norm_slot or "pt" in norm_slot:
        start_min, end_min = 480, 620
        label, cutoff = "Slot 1 (08:00 - 10:00 AM)", "10:20 AM"
    elif "2" in norm_slot or "two" in norm_slot or "theory" in norm_slot:
        start_min, end_min = 630, 800
        label, cutoff = "Slot 2 (10:30 AM - 01:00 PM)", "01:20 PM"
    elif "3" in norm_slot or "three" in norm_slot or "drill" in norm_slot:
        start_min, end_min = 840, 1040
        label, cutoff = "Slot 3 (02:00 - 05:00 PM)", "05:20 PM"
    else:
        start_min, end_min = 480, 620
        label, cutoff = slot, "cutoff time"

    if current_minutes < start_min:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{label} attendance is not yet open. It will unlock at the scheduled slot start time."
        )
    if current_minutes > end_min:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{label} attendance is locked for leaders. The allowed marking window closed at {cutoff}."
        )

async def check_teacher_attendance_lock(date_str: str, current_user: Dict[str, Any], db: AsyncIOMotorDatabase):
    """
    Enforces the 48-hour attendance rule for teachers:
    1. Attendance for a date unlocks at Slot 1 start (08:00 AM IST of that date).
    2. Teachers can view and edit attendance for 48 hours from Slot 1 start.
    3. After 48 hours, attendance is strictly locked for teachers.
    4. Admin can bypass or explicitly unlock/lock dates.
    """
    if current_user.get("role") != "teacher":
        return

    clean_date = str(date_str).strip()
    now_ist = get_ist_now()
    ist_tz = timezone(timedelta(hours=5, minutes=30))

    # Check explicit admin lock/unlock in attendance_locks
    lock_doc = await db.attendance_locks.find_one({"date": clean_date})
    if lock_doc:
        if lock_doc.get("locked") is False:
            can_edit_until = lock_doc.get("can_edit_until")
            if can_edit_until:
                try:
                    clean_str = str(can_edit_until).replace("Z", "+00:00")
                    deadline_dt = datetime.fromisoformat(clean_str).astimezone(ist_tz)
                    if now_ist <= deadline_dt:
                        return  # Admin explicitly unlocked and within deadline
                except Exception:
                    pass
        elif lock_doc.get("locked") is True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Attendance for date '{clean_date}' has been locked by Administrator."
            )

    try:
        slot1_start, lock_deadline = compute_slot1_start_and_deadline_ist(clean_date)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: '{clean_date}'. Expected YYYY-MM-DD."
        )

    if now_ist < slot1_start:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance for {clean_date} is not yet open. It unlocks at 08:00 AM IST on {clean_date}."
        )

    if now_ist > lock_deadline:
        cutoff_label = lock_deadline.strftime("%d-%b-%Y %I:%M %p IST")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance for {clean_date} is locked: the 48-hour editing window expired at {cutoff_label}. Please contact an Administrator to unlock."
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
    """Mark attendance for a cadet in a slot with upsert and 48-hour lock check."""
    check_leader_slot_lock(record.slot, record.date, current_user)
    await check_teacher_attendance_lock(record.date, current_user, db)

    query = {
        "student_id": record.student_id,
        "date": record.date,
        "slot": record.slot
    }
    
    existing = await db.attendance.find_one(query)
    if existing:
        is_locked, _, can_edit_until = compute_lock_status(existing)
        if is_locked and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Attendance record is locked: cannot be modified after 48 hours of slot unlock (expired at {can_edit_until})."
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
    Uses high-speed MongoDB bulk_write to prevent timeouts and enforces 48-hour rule.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    default_marker = current_user.get("full_name") or current_user.get("username")

    if not payload.records:
        return []

    # 1. Fast pre-validation per UNIQUE date (O(1) checks instead of 100+ separate checks)
    affected_dates = {item.date for item in payload.records}
    for d in affected_dates:
        await check_teacher_attendance_lock(d, current_user, db)

    for item in payload.records:
        check_leader_slot_lock(item.slot, item.date, current_user)

    # 2. Build bulk write operations (executed in a single network roundtrip to MongoDB)
    operations = []
    for item in payload.records:
        query = {
            "student_id": item.student_id,
            "date": item.date,
            "slot": item.slot
        }
        item_id = item.id or f"att-{uuid.uuid4().hex[:8]}"
        created_at = item.created_at or now_iso
        uploaded_at = item.uploaded_at or now_iso

        operations.append(
            UpdateOne(
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
                upsert=True
            )
        )

    if operations:
        await db.attendance.bulk_write(operations, ordered=False)

    # 3. Retrieve saved records for affected dates
    cursor = db.attendance.find({"date": {"$in": list(affected_dates)}}).sort([("date", -1), ("slot", 1)])
    saved_records = []
    async for doc in cursor:
        saved_records.append(doc_to_attendance_out(doc))

    # 4. Broadcast real-time update to all active clients (students, teachers, admins)
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
    
    check_leader_slot_lock(existing.get("slot"), existing.get("date"), current_user)
    await check_teacher_attendance_lock(existing.get("date"), current_user, db)

    is_locked, _, can_edit_until = compute_lock_status(existing)
    if is_locked and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance record is locked: cannot be modified after 48 hours of slot unlock (expired at {can_edit_until})."
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

    check_leader_slot_lock(existing.get("slot"), existing.get("date"), current_user)
    await check_teacher_attendance_lock(existing.get("date"), current_user, db)

    is_locked, _, can_edit_until = compute_lock_status(existing)
    if is_locked and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Attendance record is locked: cannot be deleted after 48 hours of slot unlock (expired at {can_edit_until})."
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
    """Reset attendance records for a specific date (restricted to 48 hours)."""
    if current_user.get("role") == "leader":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leaders cannot clear day attendance. Please contact an administrator."
        )
    await check_teacher_attendance_lock(date, current_user, db)
    filter_q = {"date": date}
    if course:
        filter_q["course"] = course

    cursor = db.attendance.find(filter_q)
    async for doc in cursor:
        is_locked, _, can_edit_until = compute_lock_status(doc)
        if is_locked and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Attendance for date '{date}' is locked: cannot be cleared after 48 hours of slot unlock (expired at {can_edit_until})."
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
    Clear all attendance muster records or for an optional course in MongoDB (Admin only).
    Used for database reset and testing.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to clear all attendance records."
        )
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

@router.post("/day/{date}/unlock")
async def unlock_day_attendance(
    date: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Admin endpoint to unlock attendance for a specific date.
    Resets the 48-hour editing window, sets is_locked=False, and broadcasts update.
    """
    clean_date = date.strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    new_deadline = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    admin_name = current_user.get("full_name") or current_user.get("username")

    await db.attendance.update_many(
        {"date": clean_date},
        {
            "$set": {
                "is_locked": False,
                "uploaded_at": now_iso,
                "can_edit_until": new_deadline,
                "unlocked_by": admin_name,
                "unlocked_at": now_iso
            }
        }
    )

    await db.attendance_locks.update_one(
        {"date": clean_date},
        {
            "$set": {
                "date": clean_date,
                "locked": False,
                "unlocked_by": admin_name,
                "unlocked_at": now_iso,
                "can_edit_until": new_deadline
            }
        },
        upsert=True
    )

    await broadcaster.broadcast({
        "event": "attendance_lock_changed",
        "date": clean_date,
        "locked": False,
        "timestamp": now_iso
    })

    return {
        "date": clean_date,
        "locked": False,
        "can_edit_until": new_deadline,
        "message": f"Attendance for {clean_date} has been unlocked for 48 hours by Administrator."
    }

@router.post("/day/{date}/lock")
async def lock_day_attendance(
    date: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Admin endpoint to lock attendance for a specific date immediately.
    """
    clean_date = date.strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    admin_name = current_user.get("full_name") or current_user.get("username")

    await db.attendance.update_many(
        {"date": clean_date},
        {
            "$set": {
                "is_locked": True,
                "can_edit_until": now_iso,
                "locked_by": admin_name,
                "locked_at": now_iso
            }
        }
    )

    await db.attendance_locks.update_one(
        {"date": clean_date},
        {
            "$set": {
                "date": clean_date,
                "locked": True,
                "locked_by": admin_name,
                "locked_at": now_iso,
                "can_edit_until": now_iso
            }
        },
        upsert=True
    )

    await broadcaster.broadcast({
        "event": "attendance_lock_changed",
        "date": clean_date,
        "locked": True,
        "timestamp": now_iso
    })

    return {
        "date": clean_date,
        "locked": True,
        "message": f"Attendance for {clean_date} has been locked by Administrator."
    }

@router.get("/day/{date}/lock-status")
async def get_day_lock_status(
    date: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    clean_date = date.strip()
    now_ist = get_ist_now()
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    role = current_user.get("role")

    lock_doc = await db.attendance_locks.find_one({"date": clean_date})
    if lock_doc:
        can_edit = lock_doc.get("can_edit_until")
        is_manually_locked = bool(lock_doc.get("locked"))
        if not is_manually_locked and can_edit:
            try:
                deadline_dt = datetime.fromisoformat(str(can_edit).replace("Z", "+00:00")).astimezone(ist_tz)
                if now_ist > deadline_dt:
                    is_manually_locked = True
            except Exception:
                pass
        
        rem_hours = 0.0
        if not is_manually_locked and can_edit:
            try:
                deadline_dt = datetime.fromisoformat(str(can_edit).replace("Z", "+00:00")).astimezone(ist_tz)
                rem_hours = max(0.0, round((deadline_dt - now_ist).total_seconds() / 3600.0, 1))
            except Exception:
                pass

        return {
            "date": clean_date,
            "locked": is_manually_locked if role != "admin" else False,
            "is_future": False,
            "can_edit_until": can_edit,
            "remaining_hours": rem_hours,
            "message": "Locked by Administrator." if is_manually_locked else f"Unlocked (Editable for {rem_hours}h)"
        }

    # Evaluate default 48-hour rule starting from Slot 1 (08:00 AM IST)
    try:
        slot1_start, lock_deadline = compute_slot1_start_and_deadline_ist(clean_date)
        is_future = now_ist < slot1_start
        is_past_48h = now_ist > lock_deadline
        is_locked = is_future or is_past_48h

        if is_future:
            rem_hours = 0.0
            msg = f"Upcoming: unlocks at 08:00 AM IST on {clean_date} (Slot 1 start)."
        elif is_past_48h:
            rem_hours = 0.0
            cutoff = lock_deadline.strftime("%d-%b-%Y %I:%M %p IST")
            msg = f"Locked: 48-hour editing window expired at {cutoff}."
        else:
            diff_sec = (lock_deadline - now_ist).total_seconds()
            rem_hours = max(0.0, round(diff_sec / 3600.0, 1))
            msg = f"Unlocked: 48-hour editing window active ({rem_hours}h remaining)."

        return {
            "date": clean_date,
            "locked": is_locked if role != "admin" else False,
            "is_future": is_future,
            "slot1_start": slot1_start.isoformat(),
            "can_edit_until": lock_deadline.isoformat(),
            "remaining_hours": rem_hours,
            "message": msg
        }
    except Exception:
        return {"date": clean_date, "locked": False, "remaining_hours": 48.0}

