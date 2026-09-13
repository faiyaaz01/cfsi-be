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
    
    # 1. Permanently remove from users collection
    await db.users.delete_many({
        "$or": [
            {"_id": user["_id"]},
            {"username": user.get("username")}
        ]
    })

    # 2. If student user, also permanently remove associated student and attendance records
    sid = user.get("student_id") or (user.get("username") if user.get("role") == "student" else None)
    if sid:
        await db.students.delete_many({
            "$or": [
                {"id": sid},
                {"roll_no": sid},
                {"_id": sid},
                {"username": sid}
            ]
        })
        await db.attendance.delete_many({"student_id": sid})
