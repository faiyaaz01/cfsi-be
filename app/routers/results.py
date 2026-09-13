from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.result import ResultOut, ResultCreate, ResultUpdate
from app.dependencies import get_current_user, require_staff

router = APIRouter(prefix="/api/results", tags=["Examination Results"])

def doc_to_result_out(doc: Dict[str, Any]) -> ResultOut:
    return ResultOut(
        id=str(doc.get("id") or doc.get("_id")),
        certificate_number=doc["certificate_number"],
        course=doc["course"],
        subject=doc["subject"],
        marks_obtained=float(doc["marks_obtained"]),
        max_marks=float(doc.get("max_marks", 100.0)),
        grade=doc["grade"],
        exam_date=doc["exam_date"],
        semester_or_term=doc["semester_or_term"],
        remarks=doc.get("remarks"),
        created_at=doc.get("created_at")
    )

@router.get("", response_model=List[ResultOut])
async def get_results(
    certificate_number: Optional[str] = None,
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetch exam results from MongoDB.
    - If student is logged in, restricted to their own certificate.
    - If admin is logged in, can view all or filter by certificate_number / course.
    """
    filter_q = {}

    if current_user.get("role") == "student":
        student_cert = current_user.get("certificate_number")
        if not student_cert:
            return []
        filter_q["certificate_number"] = student_cert
    elif certificate_number:
        filter_q["certificate_number"] = certificate_number

    if course:
        filter_q["course"] = course

    cursor = db.results.find(filter_q).sort("exam_date", -1)
    results = []
    async for doc in cursor:
        results.append(doc_to_result_out(doc))
    return results

@router.post("", response_model=ResultOut, status_code=status.HTTP_201_CREATED)
async def create_result(
    record: ResultCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Publish a new examination result in MongoDB (Admin only)."""
    new_id = record.id or f"res-{uuid.uuid4().hex[:8]}"
    created_at = record.created_at or datetime.now(timezone.utc).isoformat()
    
    doc = {
        "_id": new_id,
        "id": new_id,
        "certificate_number": record.certificate_number,
        "course": record.course,
        "subject": record.subject,
        "marks_obtained": record.marks_obtained,
        "max_marks": record.max_marks,
        "grade": record.grade,
        "exam_date": record.exam_date,
        "semester_or_term": record.semester_or_term,
        "remarks": record.remarks,
        "created_at": created_at
    }
    await db.results.insert_one(doc)
    return doc_to_result_out(doc)

@router.put("/{result_id}", response_model=ResultOut)
async def update_result(
    result_id: str,
    update_data: ResultUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Update result scores or remarks in MongoDB (Admin only)."""
    update_fields = {}
    if update_data.course is not None:
        update_fields["course"] = update_data.course
    if update_data.subject is not None:
        update_fields["subject"] = update_data.subject
    if update_data.marks_obtained is not None:
        update_fields["marks_obtained"] = update_data.marks_obtained
    if update_data.max_marks is not None:
        update_fields["max_marks"] = update_data.max_marks
    if update_data.grade is not None:
        update_fields["grade"] = update_data.grade
    if update_data.exam_date is not None:
        update_fields["exam_date"] = update_data.exam_date
    if update_data.semester_or_term is not None:
        update_fields["semester_or_term"] = update_data.semester_or_term
    if update_data.remarks is not None:
        update_fields["remarks"] = update_data.remarks

    doc = await db.results.find_one_and_update(
        {"$or": [{"_id": result_id}, {"id": result_id}]},
        {"$set": update_fields},
        return_document=True
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Result record not found")
    return doc_to_result_out(doc)

@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    result_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_staff)
):
    """Delete an examination result from MongoDB (Admin only)."""
    res = await db.results.delete_one({"$or": [{"_id": result_id}, {"id": result_id}]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Result record not found")
    return None
