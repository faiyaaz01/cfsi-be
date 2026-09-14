import re
from datetime import datetime, timedelta
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

def normalize_birth_date_and_password(birth_date: str) -> tuple[str, str]:
    """
    Returns (clean_birth_date_dmy, dob_password_ddmmyyyy).
    Handles:
    - DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    - YYYY-MM-DD, YYYY/MM/DD
    - Excel serial numbers like 36474.00011574074
    - 8-digit strings
    """
    if not birth_date:
        return ("01-01-2006", "01012006")
    
    clean = str(birth_date).strip()
    
    # 1. DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    m_dmy = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", clean)
    if m_dmy:
        p1, p2, yyyy = int(m_dmy.group(1)), int(m_dmy.group(2)), m_dmy.group(3)
        dd, mm = p1, p2
        if p2 > 12 and p1 <= 12:
            dd, mm = p2, p1
        dd_s = str(dd).zfill(2)
        mm_s = str(mm).zfill(2)
        return (f"{dd_s}-{mm_s}-{yyyy}", f"{dd_s}{mm_s}{yyyy}")
    
    # 2. YYYY-MM-DD or YYYY/MM/DD
    m_ymd = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", clean)
    if m_ymd:
        yyyy, mm, dd = m_ymd.group(1), m_ymd.group(2).zfill(2), m_ymd.group(3).zfill(2)
        return (f"{dd}-{mm}-{yyyy}", f"{dd}{mm}{yyyy}")
    
    # 3. Excel serial date (e.g. 36474.00011574074)
    try:
        num = float(clean)
        if 1000 < num < 100000:
            d = datetime(1899, 12, 30) + timedelta(days=num)
            dd_s = str(d.day).zfill(2)
            mm_s = str(d.month).zfill(2)
            yyyy_s = str(d.year)
            return (f"{dd_s}-{mm_s}-{yyyy_s}", f"{dd_s}{mm_s}{yyyy_s}")
    except Exception:
        pass
    
    # 4. 8 digits
    digits = re.sub(r"\D", "", clean)
    if len(digits) == 8:
        if digits.startswith(("19", "20")):
            yyyy, mm, dd = digits[:4], digits[4:6], digits[6:8]
            return (f"{dd}-{mm}-{yyyy}", f"{dd}{mm}{yyyy}")
        dd, mm, yyyy = digits[:2], digits[2:4], digits[4:8]
        return (f"{dd}-{mm}-{yyyy}", digits)
    
    return (clean, digits[:8] if len(digits) >= 8 else "01012006")

def format_dob_password(birth_date: str) -> str:
    _, pwd = normalize_birth_date_and_password(birth_date)
    return pwd

def format_student_id(batch: str, roll_no: str) -> str:
    """
    Generates cadet user ID based on Batch/Year (e.g. 2026-2027 -> 2627) and Roll Number.
    E.g. Roll No '1' -> '262701'.
    """
    clean_roll = str(roll_no or "").strip()
    clean_batch = str(batch or "Batch 2026-2027").strip()
    digits = re.sub(r"\D", "", clean_batch)
    prefix = "2627"
    if len(digits) >= 8:
        prefix = f"{digits[2:4]}{digits[6:8]}"
    elif len(digits) == 4:
        prefix = digits
    
    roll_padded = clean_roll.zfill(2) if len(clean_roll) < 2 and clean_roll.isdigit() else clean_roll
    return f"{prefix}{roll_padded}"

def doc_to_student_out(doc: Dict[str, Any]) -> StudentOut:
    return StudentOut(
        id=str(doc.get("id") or doc.get("_id")),
        roll_no=doc.get("roll_no") or str(doc.get("id") or doc.get("_id")),
        enrollment_no=doc.get("enrollment_no") or str(doc.get("id") or doc.get("_id")),
        name=doc.get("name", ""),
        father_name=doc.get("father_name", ""),
        course=doc.get("course", "Diploma In Fire Safety"),
        batch=doc.get("batch", "Batch 2026-2027"),
        passing_year=str(doc.get("passing_year", "2027")),
        grade=doc.get("grade", "Active Student"),
        percentage=str(doc.get("percentage", "N/A")),
        verification_status=doc.get("verification_status", "Verified"),
        issue_date=doc.get("issue_date", "Ongoing"),
        center_location=doc.get("center_location") or doc.get("center_name") or "CFSI Vadodara Main Campus, Gujarat",
        center_name=doc.get("center_name") or doc.get("center_location") or "CFSI Vadodara Main Campus, Gujarat",
        mode=doc.get("mode", "REGULAR"),
        gender=doc.get("gender", "MALE"),
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
        session_year=doc.get("session_year"),
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

    def get_roll_sort_key(s: StudentOut):
        raw = getattr(s, "roll_no", None)
        if raw is not None and str(raw).strip():
            m = re.search(r"\d+", str(raw).strip())
            if m:
                return (0, int(m.group()))
            return (1, str(raw).strip().lower())
        sid = getattr(s, "student_id", None) or getattr(s, "id", None) or ""
        m = re.search(r"\d+", str(sid).strip())
        if m:
            return (2, int(m.group()))
        return (3, str(getattr(s, "name", "")).lower())

    results.sort(key=get_roll_sort_key)
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
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}},
            {"enrollment_no": {"$regex": regex_pattern, "$options": "i"}}
        ]
    })
    if not doc:
        # If student record doesn't exist yet, create a baseline profile doc
        doc = {
            "_id": clean_id,
            "id": clean_id,
            "enrollment_no": clean_id,
            "roll_no": clean_id[-2:] if len(clean_id) >= 2 else clean_id,
            "name": current_user.get("full_name") or current_user.get("username"),
            "father_name": "",
            "course": current_user.get("course") or "DIPLOMA IN FIRE AND SAFETY MANAGEMENT",
            "batch": current_user.get("batch") or "Batch 2026-2027",
            "passing_year": "2027",
            "grade": "Active Student",
            "percentage": "N/A",
            "verification_status": "Verified",
            "issue_date": "Ongoing",
            "center_location": current_user.get("center") or "CENTRAL FIRE AND SAFETY INSTITUTE",
            "center_name": current_user.get("center") or "CENTRAL FIRE AND SAFETY INSTITUTE",
            "mode": "REGULAR",
            "gender": current_user.get("gender") or "MALE",
            "photo_url": current_user.get("photo_url"),
            "nationality": "INDIAN",
            "state": "GUJARAT"
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
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}},
            {"enrollment_no": {"$regex": regex_pattern, "$options": "i"}}
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
        "mother_name": payload.mother_name if payload.mother_name is not None else doc.get("mother_name"),
        "birth_date": payload.birth_date if payload.birth_date is not None else doc.get("birth_date"),
        "gender": payload.gender.strip().upper() if payload.gender else doc.get("gender", "MALE"),
        "present_address": payload.present_address if payload.present_address is not None else doc.get("present_address"),
        "student_phone": payload.student_phone.strip(),
        "father_phone": payload.father_phone.strip() if payload.father_phone else None,
        "mother_phone": payload.mother_phone.strip() if payload.mother_phone else None,
        "category": payload.category if payload.category is not None else doc.get("category"),
        "aadhar_card": payload.aadhar_card.strip() if payload.aadhar_card else None,
        "email": payload.email.strip() if payload.email else None,
        "nationality": payload.nationality or doc.get("nationality", "INDIAN"),
        "state": payload.state or doc.get("state", "GUJARAT"),
    }
    if payload.center_name or payload.center_location:
        c_name = payload.center_name or payload.center_location
        update_fields["center_location"] = c_name
        update_fields["center_name"] = c_name
    if payload.mode:
        update_fields["mode"] = payload.mode.strip().upper()
    if payload.photo_url is not None:
        update_fields["photo_url"] = payload.photo_url

    await db.students.update_one({"_id": doc["_id"]}, {"$set": update_fields})
    
    # Sync name, photo, gender, phone, email with user account if changed
    user_updates = {
        "full_name": update_fields["name"],
        "phone": update_fields["student_phone"],
        "gender": update_fields["gender"],
    }
    if update_fields.get("email"):
        user_updates["email"] = update_fields["email"]
    if payload.photo_url is not None:
        user_updates["photo_url"] = payload.photo_url
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

    for idx, item in enumerate(payload.students):
        batch_val = item.batch or payload.default_batch or "Batch 2026-2027"
        raw_enrollment = (item.enrollment_no or "").strip()
        clean_roll = str(item.roll_no or "").strip()
        if not clean_roll:
            clean_roll = str(idx + 1)

        # Automatic Cadet User ID assigned as per roll (e.g. 262701) if not explicitly provided
        cadet_user_id = (item.student_id or "").strip()
        if not cadet_user_id:
            cadet_user_id = format_student_id(batch_val, clean_roll)

        student_id = cadet_user_id
        clean_dob, dob_password = normalize_birth_date_and_password(item.birth_date)

        center_val = item.center_name or item.center_location or "CENTRAL FIRE AND SAFETY INSTITUTE"

        student_doc = {
            "_id": student_id,
            "id": student_id,
            "student_id": student_id,
            "enrollment_no": raw_enrollment if raw_enrollment else student_id,
            "session_year": (item.session_year or "").strip(),
            "roll_no": clean_roll,
            "name": item.name.strip(),
            "father_name": item.father_name.strip() if item.father_name else "",
            "mother_name": item.mother_name.strip() if item.mother_name else "",
            "birth_date": clean_dob,
            "gender": (item.gender or "MALE").strip().upper(),
            "course": item.course or "DIPLOMA IN FIRE AND SAFETY MANAGEMENT",
            "batch": batch_val,
            "passing_year": item.passing_year or "2027",
            "grade": item.grade or "Active Student",
            "percentage": item.percentage or "N/A",
            "verification_status": item.verification_status or "Verified",
            "issue_date": item.issue_date or "Ongoing",
            "center_location": center_val,
            "center_name": center_val,
            "mode": (item.mode or "REGULAR").strip().upper(),
            "photo_url": item.photo_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80",
            "present_address": item.present_address or "",
            "student_phone": item.student_phone or "",
            "father_phone": item.father_phone or "",
            "mother_phone": item.mother_phone or "",
            "category": item.category or "General",
            "aadhar_card": item.aadhar_card or "",
            "email": item.email or f"{student_id.lower()}@cfsi.edu.in",
            "nationality": item.nationality or "INDIAN",
            "state": item.state or "GUJARAT",
        }

        # Check existing student by cadet_user_id or enrollment_no
        search_filter = [{"id": student_id}, {"_id": student_id}, {"student_id": student_id}]
        if raw_enrollment:
            search_filter.append({"enrollment_no": raw_enrollment})
        existing_student = await db.students.find_one({"$or": search_filter})
        status_label = "Updated" if existing_student else "Created"
        if existing_student:
            updated_count += 1
            await db.students.update_one({"_id": existing_student["_id"]}, {"$set": student_doc})
        else:
            created_count += 1
            await db.students.insert_one(student_doc)

        # Hash password (custom if provided, else birth date DDMMYYYY) with bcrypt
        effective_pwd = item.password.strip() if getattr(item, "password", None) and str(item.password).strip() else dob_password
        pwd_hash = hash_password(effective_pwd)

        # Upsert corresponding user login account with Cadet User ID (e.g. 262701) as username
        user_account = {
            "username": student_id,
            "student_id": student_id,
            "enrollment_no": raw_enrollment if raw_enrollment else student_id,
            "session_year": (item.session_year or "").strip(),
            "role": "student",
            "full_name": item.name.strip(),
            "photo_url": student_doc["photo_url"],
            "gender": student_doc["gender"],
            "course": student_doc["course"],
            "batch": student_doc["batch"],
            "center": student_doc["center_location"],
            "phone": student_doc["student_phone"],
            "email": student_doc["email"],
            "password_hash": pwd_hash,
            "is_active": item.is_active if getattr(item, "is_active", None) is not None else True,
            "token_version": 0,
        }

        user_search_filter = [{"username": student_id}, {"student_id": student_id}]
        if raw_enrollment:
            user_search_filter.append({"enrollment_no": raw_enrollment})

        await db.users.update_one(
            {"$or": user_search_filter},
            {
                "$set": user_account,
                "$setOnInsert": {"_id": f"user-student-{student_id}"}
            },
            upsert=True
        )

        summary_list.append(BulkImportStudentSummary(
            student_id=student_id,
            roll_no=clean_roll,
            enrollment_no=student_id,
            name=item.name.strip(),
            birth_date=clean_dob,
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
        user_enr = (current_user.get("enrollment_no") or "").lower()
        if clean_id.lower() not in (user_sid, user_uname, user_enr):
            raise HTTPException(status_code=403, detail="You can only access your own student record")
    regex_pattern = f"^{re.escape(clean_id)}$"
    doc = await db.students.find_one({
        "$or": [
            {"id": {"$regex": regex_pattern, "$options": "i"}},
            {"roll_no": {"$regex": regex_pattern, "$options": "i"}},
            {"enrollment_no": {"$regex": regex_pattern, "$options": "i"}}
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

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Permanently delete a student cadet record, their user login account, and all their attendance data from MongoDB (Admin only).
    """
    clean_id = student_id.strip()
    student = await db.students.find_one({
        "$or": [
            {"id": clean_id},
            {"roll_no": clean_id},
            {"_id": clean_id},
            {"student_id": clean_id}
        ]
    })

    # Collect all possible candidate IDs
    candidate_ids = {clean_id}
    roll_no = None
    course = None
    if student:
        for k in ["id", "_id", "student_id", "enrollment_no"]:
            v = student.get(k)
            if v:
                candidate_ids.add(str(v).strip())
        if student.get("roll_no"):
            roll_no = str(student["roll_no"]).strip()
        if student.get("course"):
            course = str(student["course"]).strip()

    # Also find any linked user to collect username and user _id
    linked_users = await db.users.find({
        "$or": [
            {"student_id": {"$in": list(candidate_ids)}},
            {"username": {"$in": list(candidate_ids)}},
            {"_id": {"$in": [f"user-student-{cid}" for cid in candidate_ids]}}
        ]
    }).to_list(length=10)

    for u in linked_users:
        if u.get("username"):
            candidate_ids.add(str(u["username"]).strip())
        if u.get("student_id"):
            candidate_ids.add(str(u["student_id"]).strip())

    id_list = list(candidate_ids)

    # 1. Permanently delete all attendance records for this cadet from db.attendance
    attendance_filters = [
        {"student_id": {"$in": id_list}},
        {"studentId": {"$in": id_list}}
    ]
    if roll_no:
        if course:
            attendance_filters.append({"roll_no": roll_no, "course": course})
            attendance_filters.append({"rollNo": roll_no, "course": course})
        else:
            attendance_filters.append({"roll_no": roll_no})
            attendance_filters.append({"rollNo": roll_no})

    await db.attendance.delete_many({"$or": attendance_filters})

    # 2. Permanently delete student document from students collection
    student_del_filters = [
        {"id": {"$in": id_list}},
        {"_id": {"$in": id_list}},
        {"student_id": {"$in": id_list}}
    ]
    if roll_no and course:
        student_del_filters.append({"roll_no": roll_no, "course": course})
    
    res = await db.students.delete_many({"$or": student_del_filters})

    # 3. Permanently delete linked user account from users collection
    user_del_filters = [
        {"student_id": {"$in": id_list}},
        {"username": {"$in": id_list}}
    ]
    for cid in id_list:
        user_del_filters.append({"_id": f"user-student-{cid}"})
    await db.users.delete_many({"$or": user_del_filters})

    # 4. Broadcast real-time SSE update so all active client sessions refresh attendance
    try:
        from app.routers.attendance import broadcaster
        await broadcaster.broadcast({
            "event": "attendance_updated",
            "action": "delete_student",
            "student_id": clean_id,
            "all_ids": id_list
        })
    except Exception:
        pass

    if res.deleted_count == 0 and not student:
        raise HTTPException(status_code=404, detail="Student record not found in database")
