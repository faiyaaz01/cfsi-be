from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError
from app.database import get_database
from app.dependencies import require_admin
from app.schemas.auth import UserCreate, UserUpdate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["User management"], dependencies=[Depends(require_admin)])

def public(user):
    return {**user, "id": str(user["_id"])}

async def find(user_id, db):
    from bson import ObjectId
    keys = [user_id]
    if ObjectId.is_valid(user_id):
        keys.append(ObjectId(user_id))
    user = await db.users.find_one({
        "$or": [
            {"_id": {"$in": keys}},
            {"username": user_id},
            {"id": user_id},
            {"student_id": user_id}
        ]
    })
    if not user:
        raise HTTPException(404, "User not found")
    return user

async def validate_link(data, db):
    if data["role"] == "student":
        sid = data.get("student_id")
        if not sid or not await db.students.find_one({"$or": [{"id": sid}, {"roll_no": sid}]}):
            raise HTTPException(422, "Students require an existing student ID")
    else:
        data["student_id"] = None

@router.get("", response_model=list[UserOut])
async def list_users(db=Depends(get_database)):
    return [public(u) async for u in db.users.find({}).sort("username", 1)]

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, db=Depends(get_database)):
    return public(await find(user_id, db))

@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db=Depends(get_database)):
    data = payload.model_dump()
    await validate_link(data, db)
    data.update(_id=str(uuid4()), token_version=0, password_hash=hash_password(data.pop("password")))
    try:
        await db.users.insert_one(data)
    except DuplicateKeyError:
        raise HTTPException(409, "Username already exists")
    return public(data)

@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, db=Depends(get_database), actor=Depends(require_admin)):
    user = await find(user_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(k) is None for k in changes if k != "student_id"):
        raise HTTPException(422, "Fields cannot be null")
    if user["_id"] == actor["_id"] and (changes.get("role", "admin") != "admin" or changes.get("is_active") is False):
        raise HTTPException(409, "You cannot demote or deactivate your own admin account")
    merged = {**user, **changes}
    await validate_link(merged, db)
    changes["student_id"] = merged.get("student_id")
    if "password" in changes:
        changes["password_hash"] = hash_password(changes.pop("password"))
    await db.users.update_one({"_id": user["_id"]}, {"$set": changes, "$inc": {"token_version": 1}})
    return public(await find(user_id, db))

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: str, db=Depends(get_database), actor=Depends(require_admin)):
    user = await find(user_id, db)
    if str(user["_id"]) == str(actor["_id"]) or user.get("username") == actor.get("username"):
        raise HTTPException(409, "You cannot delete your own admin account")
    
    # 1. Collect all candidate identifiers from user document
    candidate_ids = set()
    for field in ["student_id", "username", "enrollment_no", "id"]:
        val = user.get(field)
        if val:
            candidate_ids.add(str(val).strip())
    if user_id:
        candidate_ids.add(str(user_id).strip())
    if str(user.get("_id")):
        candidate_ids.add(str(user["_id"]).strip())

    # 2. Find any corresponding student record(s) in students collection
    student_lookup = []
    for cand in candidate_ids:
        student_lookup.extend([
            {"id": cand},
            {"_id": cand},
            {"student_id": cand},
            {"roll_no": cand}
        ])
    
    students = await db.students.find({"$or": student_lookup}).to_list(length=20) if student_lookup else []
    
    # Collect additional IDs and roll/course details from student records
    roll_course_pairs = []
    for s in students:
        for key in ["id", "_id", "student_id", "enrollment_no"]:
            val = s.get(key)
            if val:
                candidate_ids.add(str(val).strip())
        r_no = str(s.get("roll_no") or "").strip()
        if r_no:
            roll_course_pairs.append({
                "roll_no": r_no,
                "course": s.get("course")
            })

    id_list = list(candidate_ids)

    # 3. Permanently remove all matching attendance records from db.attendance
    attendance_filters = []
    if id_list:
        attendance_filters.append({"student_id": {"$in": id_list}})
        attendance_filters.append({"studentId": {"$in": id_list}})
    
    for pair in roll_course_pairs:
        r = pair["roll_no"]
        c = pair["course"]
        if c:
            attendance_filters.append({"roll_no": r, "course": c})
            attendance_filters.append({"rollNo": r, "course": c})
        else:
            attendance_filters.append({"roll_no": r})
            attendance_filters.append({"rollNo": r})

    if attendance_filters:
        await db.attendance.delete_many({"$or": attendance_filters})

    # 4. Permanently remove matching student record(s) from db.students
    student_del_filters = []
    if id_list:
        student_del_filters.extend([
            {"id": {"$in": id_list}},
            {"_id": {"$in": id_list}},
            {"student_id": {"$in": id_list}}
        ])
    for pair in roll_course_pairs:
        if pair["course"]:
            student_del_filters.append({"roll_no": pair["roll_no"], "course": pair["course"]})
    
    if student_del_filters:
        await db.students.delete_many({"$or": student_del_filters})

    # 5. Permanently remove user record(s) from db.users
    user_del_filters = [
        {"_id": user["_id"]},
        {"username": user.get("username")}
    ]
    if id_list:
        user_del_filters.append({"student_id": {"$in": id_list}})
        user_del_filters.append({"username": {"$in": id_list}})
    await db.users.delete_many({"$or": user_del_filters})

    # 6. Broadcast real-time SSE update so all active client sessions refresh
    try:
        from app.routers.attendance import broadcaster
        await broadcaster.broadcast({
            "event": "attendance_updated",
            "action": "delete_user",
            "user_id": str(user_id),
            "student_ids": id_list
        })
    except Exception:
        pass
