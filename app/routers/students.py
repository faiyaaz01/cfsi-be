import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.student import (
    StudentOut,
    StudentCreate,
    StudentProfileUpdate,
    BulkImportRequest,
    BulkImportResult,
    BulkImportStudentSummary,
)
from app.dependencies import get_current_user, require_admin
from app.security import hash_password

router = APIRouter(prefix="/api/students", tags=["Students & Registry"])

def format_dob_password(birth_date: str) -> str:
    """
    Extracts digits from birth date into DDMMYYYY format for student passwords.
    E.g. '23/10/2006' -> '23102006', '2006-10-23' -> '23102006', '23-10-2006' -> '23102006'.
    """
    if not birth_date:
        return "20060101"
    
    clean = str(birth_date).strip()
    
    # Check YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
    m_ymd = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", clean)
    if m_ymd:
        yyyy, mm, dd = m_ymd.group(1), m_ymd.group(2).zfill(2), m_ymd.group(3).zfill(2)
        return f"{dd}{mm}{yyyy}"
    
    # Check DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    m_dmy = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", clean)
    if m_dmy:
        dd, mm, yyyy = m_dmy.group(1).zfill(2), m_dmy.group(2).zfill(2), m_dmy.group(3)
        return f"{dd}{mm}{yyyy}"
    
    # Check if only 8 digits
    digits = re.sub(r"\D", "", clean)
    if len(digits) == 8:
        # If starts with 19 or 20 (YYYYMMDD), convert to DDMMYYYY
        if digits.startswith(("19", "20")):
            yyyy = digits[:4]
            mm = digits[4:6]
            dd = digits[6:8]
            return f"{dd}{mm}{yyyy}"
        return digits
    
    return digits if digits else "20060101"

def format_student_id(batch: str, roll_no: str) -> str:
    """
    Generates student ID based on Batch (e.g. 2026-2027 -> 2627) and Roll Number.
    E.g. Roll No '01' -> '262701'. If roll_no is already like '262701', keeps it.
    """
    clean_roll = str(roll_no).strip()
    if len(clean_roll) >= 5 and clean_roll.isdigit():
        return clean_roll
    
    clean_batch = batch or "Batch 2026-2027"
    digits = re.sub(r"\D", "", clean_batch)
    prefix = "2627"
    if len(digits) >= 8:
        prefix = f"{digits[2:4]}{digits[6:8]}"
    elif len(digits) == 4:
        prefix = digits
    
    # Pad roll no to at least 2 digits (e.g. '1' -> '01')
    roll_padded = clean_roll.zfill(2) if len(clean_roll) < 2 else clean_roll
    return f"{prefix}{roll_padded}"

def doc_to_student_out(doc: Dict[str, Any]) -> StudentOut:
    return StudentOut(
        id=str(doc.get("id") or doc.get("_id")),
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
        photo_url=doc.get("photo_url"),
        mother_name=doc.get("mother_name"),
        birth_date=doc.get("birth_date"),
        present_address=doc.get("present_address"),
        student_phone=doc.get("student_phone"),
        father_phone=doc.get("father_phone"),
        mother_phone=doc.get("mother_phone"),
        category=doc.get("category"),
        aadhar_card=doc.get("aadhar_card"),
        email=doc.get("email"),
        nationality=doc.get("nationality", "Indian"),
        state=doc.get("state", "Gujarat")
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
        student_id = current_user.get("student_id") or current_user.get("username")
        if not student_id:
            return []
        filter_q["$or"] = [
            {"id": {"$regex": f"^{re.escape(student_id)}$", "$options": "i"}},
            {"roll_no": {"$regex": f"^{re.escape(student_id)}$", "$options": "i"}}
        ]
    cursor = db.students.find(filter_q)
    results = []
    async for doc in cursor:
        results.append(doc_to_student_out(doc))
    return results

@router.get("/profile/me", response_model=StudentOut)
async def get_my_profile(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve the profile of the currently logged in student."""
    sid = current_user.get("student_id") or current_user.get("username")
    if not sid:
        raise HTTPException(status_code=404, detail="No student ID associated with this account")
    
    clean_id = sid.strip()
    regex_pattern = f"^{re.escape(clean_id)}$"
    doc = await db.students.find_one({
        "$or": [
            {"id": {"$regex": regex_pattern, "$options": "i"}},
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}}
        ]
    })
    if not doc:
        # If student record doesn't exist yet, create a baseline profile doc
        doc = {
            "_id": clean_id,
            "id": clean_id,
            "roll_no": clean_id[-2:] if len(clean_id) >= 2 else clean_id,
            "name": current_user.get("full_name") or current_user.get("username"),
            "father_name": "",
            "course": "Fire Safety Program",
            "batch": "Batch 2026-2027",
            "passing_year": "2027",
            "grade": "Active Cadet",
            "percentage": "N/A",
            "verification_status": "Verified",
            "issue_date": "Ongoing",
            "center_location": "CFSI Vadodara Main Campus, Gujarat",
            "photo_url": current_user.get("photo_url"),
            "nationality": "Indian",
            "state": "Gujarat"
        }
        await db.students.insert_one(doc)
    return doc_to_student_out(doc)

@router.put("/profile/me", response_model=StudentOut)
async def update_my_profile(
    payload: StudentProfileUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update profile fields for the currently logged in student."""
    sid = current_user.get("student_id") or current_user.get("username")
    if not sid:
        raise HTTPException(status_code=404, detail="No student ID associated with this account")
    
    clean_id = sid.strip()
    regex_pattern = f"^{re.escape(clean_id)}$"
    doc = await db.students.find_one({
        "$or": [
            {"id": {"$regex": regex_pattern, "$options": "i"}},
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}}
        ]
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Student record not found")
    
    # Enforce mandatory student phone number
    if not payload.student_phone or not payload.student_phone.strip():
        raise HTTPException(status_code=422, detail="Student phone number is mandatory")

    update_fields = {
        "name": payload.name if payload.name is not None else doc.get("name"),
        "father_name": payload.father_name if payload.father_name is not None else doc.get("father_name"),
        "mother_name": payload.mother_name,
        "birth_date": payload.birth_date,
        "present_address": payload.present_address,
        "student_phone": payload.student_phone.strip(),
        "father_phone": payload.father_phone.strip() if payload.father_phone else None,
        "mother_phone": payload.mother_phone.strip() if payload.mother_phone else None,
        "category": payload.category,
        "aadhar_card": payload.aadhar_card.strip() if payload.aadhar_card else None,
        "email": payload.email.strip() if payload.email else None,
        "nationality": payload.nationality or "Indian",
        "state": payload.state or "Gujarat",
    }
    if payload.photo_url is not None:
        update_fields["photo_url"] = payload.photo_url

    await db.students.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    
    # Sync name and photo with user account if changed
    user_updates = {}
    if payload.name:
        user_updates["full_name"] = payload.name
    if payload.photo_url is not None:
        user_updates["photo_url"] = payload.photo_url
    if user_updates:
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": user_updates})

    updated_doc = await db.students.find_one({"_id": doc["_id"]})
    return doc_to_student_out(updated_doc)

@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_students(
    payload: BulkImportRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Bulk import students from CSV/XLS data and automatically generate login user accounts.
    - Student ID: derived from batch & roll number (e.g. 262701)
    - Password: generated from birth date formatted as DDMMYYYY (e.g. 23/10/2006 -> 23102006)
    """
    if not payload.students:
        raise HTTPException(status_code=400, detail="No student records provided for import")
    
    created_count = 0
    updated_count = 0
    summary_list = []

    for item in payload.students:
        batch_val = item.batch or payload.default_batch or "Batch 2026-2027"
        student_id = format_student_id(batch_val, item.roll_no)
        dob_password = format_dob_password(item.birth_date)
        clean_roll = str(item.roll_no).strip()
        if len(clean_roll) < 2 and clean_roll.isdigit():
            clean_roll = clean_roll.zfill(2)

        student_doc = {
            "_id": student_id,
            "id": student_id,
            "roll_no": clean_roll,
            "name": item.name.strip(),
            "father_name": item.father_name.strip() if item.father_name else "",
            "mother_name": item.mother_name.strip() if item.mother_name else "",
            "birth_date": item.birth_date.strip(),
            "course": item.course or "Diploma In Fire Safety",
            "batch": batch_val,
            "passing_year": item.passing_year or "2027",
            "grade": item.grade or "Active Cadet",
            "percentage": item.percentage or "N/A",
            "verification_status": item.verification_status or "Verified",
            "issue_date": item.issue_date or "Ongoing",
            "center_location": item.center_location or "CFSI Vadodara Main Campus, Gujarat",
            "photo_url": item.photo_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80",
            "present_address": item.present_address or "",
            "student_phone": item.student_phone or "",
            "father_phone": item.father_phone or "",
            "mother_phone": item.mother_phone or "",
            "category": item.category or "General",
            "aadhar_card": item.aadhar_card or "",
            "email": item.email or f"{student_id}@cfsi.edu.in",
            "nationality": item.nationality or "Indian",
            "state": item.state or "Gujarat",
        }

        # Check existing student
        existing_student = await db.students.find_one({"id": student_id})
        status_label = "Updated" if existing_student else "Created"
        if existing_student:
            updated_count += 1
            await db.students.update_one({"id": student_id}, {"$set": student_doc})
        else:
            created_count += 1
            await db.students.insert_one(student_doc)

        # Hash birthdate password with bcrypt
        pwd_hash = hash_password(dob_password)

        # Upsert corresponding user login account with Student ID as username
        user_account = {
            "username": student_id,
            "student_id": student_id,
            "role": "student",
            "full_name": item.name.strip(),
            "photo_url": student_doc["photo_url"],
            "password_hash": pwd_hash,
            "is_active": True,
            "token_version": 0,
        }

        await db.users.update_one(
            {"username": student_id},
            {
                "$set": user_account,
                "$setOnInsert": {"_id": f"user-student-{student_id}"}
            },
            upsert=True
        )

        summary_list.append(BulkImportStudentSummary(
            student_id=student_id,
            roll_no=clean_roll,
            name=item.name.strip(),
            birth_date=item.birth_date.strip(),
            generated_password=dob_password,
            status=status_label
        ))

    return BulkImportResult(
        success=True,
        message=f"Processed {len(payload.students)} students: {created_count} created, {updated_count} updated. Login accounts generated with birthdate passwords.",
        total_processed=len(payload.students),
        created_count=created_count,
        updated_count=updated_count,
        students=summary_list
    )

@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetch details of a single student by student ID or roll no."""
    clean_id = student_id.strip()
    if current_user["role"] == "student":
        user_sid = (current_user.get("student_id") or "").lower()
        user_uname = (current_user.get("username") or "").lower()
        if clean_id.lower() not in (user_sid, user_uname):
            raise HTTPException(status_code=403, detail="You can only access your own cadet record")
    regex_pattern = f"^{re.escape(clean_id)}$"
    doc = await db.students.find_one({
        "$or": [
            {"id": {"$regex": regex_pattern, "$options": "i"}},
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}}
        ]
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
    """Create a new student cadet entry in MongoDB (Admin only)."""
    existing = await db.students.find_one({"id": student_in.id})
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    
    doc = {
        "_id": student_in.id,
        "id": student_in.id,
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
        "photo_url": student_in.photo_url,
        "mother_name": student_in.mother_name,
        "birth_date": student_in.birth_date,
        "present_address": student_in.present_address,
        "student_phone": student_in.student_phone,
        "father_phone": student_in.father_phone,
        "mother_phone": student_in.mother_phone,
        "category": student_in.category,
        "aadhar_card": student_in.aadhar_card,
        "email": student_in.email,
        "nationality": student_in.nationality or "Indian",
        "state": student_in.state or "Gujarat"
    }
    await db.students.insert_one(doc)
    return doc_to_student_out(doc)
