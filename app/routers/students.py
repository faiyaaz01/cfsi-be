import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.student import StudentOut, StudentCreate, StudentVerifyResponse
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/students", tags=["Students & Verification"])

def doc_to_student_out(doc: Dict[str, Any]) -> StudentOut:
    return StudentOut(
        id=str(doc.get("id") or doc.get("_id")),
        certificate_number=doc["certificate_number"],
        roll_no=doc["roll_no"],
        name=doc["name"],
        father_name=doc["father_name"],
        course=doc["course"],
        batch=doc["batch"],
        passing_year=str(doc["passing_year"]),
        grade=doc["grade"],
        percentage=str(doc["percentage"]),
        verification_status=doc.get("verification_status", "Verified"),
        issue_date=doc["issue_date"],
        center_location=doc["center_location"],
        photo_url=doc.get("photo_url")
    )

@router.get("", response_model=List[StudentOut])
async def list_students(
    course: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List enrolled students/cadets. Requires authentication.
    """
    filter_q = {}
    if course:
        filter_q["course"] = course
    
    if current_user["role"] == "student":
        if not current_user.get("certificate_number"):
            return []
        filter_q["certificate_number"] = current_user["certificate_number"]
    cursor = db.students.find(filter_q)
    results = []
    async for doc in cursor:
        results.append(doc_to_student_out(doc))
    return results

@router.get("/verify/{certificate_number}", response_model=StudentVerifyResponse)
async def verify_certificate(
    certificate_number: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)  # Enforce verify certificate AFTER login only!
):
    """
    Verify student certificate authenticity in MongoDB.
    NOTE: As requested, this action requires an authenticated session (JWT).
    """
    clean_cert = certificate_number.strip()
    if current_user["role"] == "student" and clean_cert.lower() != (current_user.get("certificate_number") or "").lower():
        raise HTTPException(status_code=403, detail="You can only access your own certificate")
    regex_pattern = f"^{re.escape(clean_cert)}$"
    doc = await db.students.find_one({
        "certificate_number": {"$regex": regex_pattern, "$options": "i"}
    })
    
    if not doc:
        return StudentVerifyResponse(
            verified=False,
            message=f"No certificate found matching identifier '{certificate_number}'",
            student=None
        )
    
    return StudentVerifyResponse(
        verified=True,
        message="Certificate verified successfully with Central Fire Safety Institute registry",
        student=doc_to_student_out(doc)
    )

@router.get("/{certificate_number}", response_model=StudentOut)
async def get_student_by_cert(
    certificate_number: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetch details of a single student by certificate number."""
    clean_cert = certificate_number.strip()
    if current_user["role"] == "student" and clean_cert.lower() != (current_user.get("certificate_number") or "").lower():
        raise HTTPException(status_code=403, detail="You can only access your own certificate")
    regex_pattern = f"^{re.escape(clean_cert)}$"
    doc = await db.students.find_one({
        "certificate_number": {"$regex": regex_pattern, "$options": "i"}
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Student record not found")
    return doc_to_student_out(doc)

@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_in: StudentCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Create a new student certificate entry in MongoDB (Admin only)."""
    existing = await db.students.find_one({"certificate_number": student_in.certificate_number})
    if existing:
        raise HTTPException(status_code=400, detail="Certificate number already exists")
    
    doc = {
        "_id": student_in.id,
        "id": student_in.id,
        "certificate_number": student_in.certificate_number,
        "roll_no": student_in.roll_no,
        "name": student_in.name,
        "father_name": student_in.father_name,
        "course": student_in.course,
        "batch": student_in.batch,
        "passing_year": student_in.passing_year,
        "grade": student_in.grade,
        "percentage": student_in.percentage,
        "verification_status": student_in.verification_status,
        "issue_date": student_in.issue_date,
        "center_location": student_in.center_location,
        "photo_url": student_in.photo_url
    }
    await db.students.insert_one(doc)
    return doc_to_student_out(doc)
