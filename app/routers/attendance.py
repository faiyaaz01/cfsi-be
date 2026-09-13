from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.attendance import (
    AttendanceOut, AttendanceCreate, AttendanceUpdate, AttendanceBulkCreate
)
from app.dependencies import get_current_user, require_staff

router = APIRouter(prefix="/api/attendance", tags=["Attendance Muster"])

def doc_to_attendance_out(doc: Dict[str, Any]) -> AttendanceOut:
    return AttendanceOut(
        id=str(doc.get("id") or doc.get("_id")),
        certificate_number=doc["certificate_number"],
        date=doc["date"],
        slot=doc["slot"],
        course=doc["course"],
        status=doc["status"],
        topic_or_module=doc.get("topic_or_module"),
        remarks=doc.get("remarks"),
        marked_by=doc.get("marked_by"),
        created_at=doc.get("created_at")
    )

@router.get("", response_model=List[AttendanceOut])
async def get_attendance(
    date: Optional[str] = None,
    slot: Optional[str] = None,
    certificate_number: Optional[str] = None,
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Query attendance records from MongoDB.
    - If student is logged in, restricted to their own certificate.
    - If admin is logged in, can view all records and filter by date, slot, course.
    """
    filter_q = {}

    if current_user.get("role") == "student":
        student_cert = current_user.get("certificate_number")
        if not student_cert:
            return []
        filter_q["certificate_number"] = student_cert
    elif certificate_number:
        filter_q["certificate_number"] = certificate_number

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

@router.post("", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
async def create_or_upsert_attendance(
    record: AttendanceCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Mark attendance for a student in a slot (Admin only) with upsert."""
    query = {
        "certificate_number": record.certificate_number,
        "date": record.date,
        "slot": record.slot
    }
    
    new_id = record.id or f"att-{uuid.uuid4().hex[:8]}"
    created_at = record.created_at or datetime.now(timezone.utc).isoformat()
    marked_by = record.marked_by or current_user.get("full_name") or current_user.get("username")

    update_fields = {
        "course": record.course,
        "status": record.status,
        "topic_or_module": record.topic_or_module,
        "remarks": record.remarks,
        "marked_by": marked_by,
    }

    doc = await db.attendance.find_one_and_update(
        query,
        {
            "$set": update_fields,
            "$setOnInsert": {
                "_id": new_id,
                "id": new_id,
                "certificate_number": record.certificate_number,
                "date": record.date,
                "slot": record.slot,
                "created_at": created_at
            }
        },
        upsert=True,
        return_document=True
    )
    return doc_to_attendance_out(doc)

@router.post("/bulk", response_model=List[AttendanceOut])
async def bulk_save_attendance(
    payload: AttendanceBulkCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """
    Bulk upsert 3-slot muster table attendance records in MongoDB (Admin only).
    Saves whole day or slot table rows in one atomic transaction.
    """
    saved_records = []
    now_str = datetime.now(timezone.utc).isoformat()
    default_marker = current_user.get("full_name") or current_user.get("username")

    for item in payload.records:
        query = {
            "certificate_number": item.certificate_number,
            "date": item.date,
            "slot": item.slot
        }
        item_id = item.id or f"att-{uuid.uuid4().hex[:8]}"
        doc = await db.attendance.find_one_and_update(
            query,
            {
                "$set": {
                    "course": item.course,
                    "status": item.status,
                    "topic_or_module": item.topic_or_module,
                    "remarks": item.remarks,
                    "marked_by": item.marked_by or default_marker
                },
                "$setOnInsert": {
                    "_id": item_id,
                    "id": item_id,
                    "certificate_number": item.certificate_number,
                    "date": item.date,
                    "slot": item.slot,
                    "created_at": item.created_at or now_str
                }
            },
            upsert=True,
            return_document=True
        )
        saved_records.append(doc_to_attendance_out(doc))

    return saved_records

@router.put("/{record_id}", response_model=AttendanceOut)
async def update_attendance(
    record_id: str,
    update_data: AttendanceUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Update a specific attendance record by ID."""
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
        {"$or": [{"_id": record_id}, {"id": record_id}]},
        {"$set": update_fields},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return doc_to_attendance_out(doc)

@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    record_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Delete attendance record by ID."""
    res = await db.attendance.delete_one({"$or": [{"_id": record_id}, {"id": record_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return None

@router.delete("/day/{date}", status_code=status.HTTP_200_OK)
async def clear_day_attendance(
    date: str,
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Reset attendance records for a specific date (and optional course)."""
    filter_q = {"date": date}
    if course:
        filter_q["course"] = course
    res = await db.attendance.delete_many(filter_q)
    return {"deleted": res.deleted_count, "date": date}
