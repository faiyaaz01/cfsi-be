import re
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.schemas.auth import LoginRequest, Token, UserOut
from app.security import verify_password, create_access_token
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Unified Login endpoint for Admin, Teacher, and Student accounts with MongoDB.
    Passwords verified via bcrypt against salted hashes.
    Issues JWT bearer token.
    """
    clean_username = login_data.username.strip()
    user = await db.users.find_one({"username": clean_username})
    if not user:
        user = await db.users.find_one({
            "$or": [
                {"username": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}},
                {"student_id": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}},
                {"enrollment_no": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}}
            ]
        })
    if not user:
        student_doc = await db.students.find_one({
            "$or": [
                {"id": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}},
                {"roll_no": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}},
                {"enrollment_no": {"$regex": f"^{re.escape(clean_username)}$", "$options": "i"}}
            ]
        })
        if student_doc:
            user = await db.users.find_one({
                "$or": [
                    {"student_id": student_doc.get("id")},
                    {"student_id": student_doc.get("roll_no")},
                    {"student_id": student_doc.get("enrollment_no")},
                    {"username": student_doc.get("id", "")},
                    {"username": student_doc.get("enrollment_no", "")}
                ]
            })
    
    if not user or not verify_password(login_data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # If the client requested specific portal role, verify compatibility
    user_role = user.get("role", "student")
    if login_data.role and login_data.role != "auto" and login_data.role != user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account does not have permission for the '{login_data.role}' portal"
        )
    
    user_id_str = str(user.get("_id", user.get("id", "")))
    token_data = {
        "sub": user["username"],
        "role": user_role,
        "student_id": user.get("student_id"),
        "user_id": user_id_str,
        "token_version": user.get("token_version", 0),
        "full_name": user.get("full_name")
    }
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    
    photo_url = user.get("photo_url")
    if not photo_url and user.get("student_id"):
        s_doc = await db.students.find_one({"$or": [{"id": user["student_id"]}, {"roll_no": user["student_id"]}]})
        if s_doc:
            photo_url = s_doc.get("photo_url")

    user_out = UserOut(
        id=user_id_str,
        username=user["username"],
        role=user_role,
        student_id=user.get("student_id"),
        full_name=user.get("full_name"),
        photo_url=photo_url,
        is_active=user.get("is_active", True)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user_role,
        user=user_out
    )

@router.get("/me", response_model=UserOut)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Return the profile of the currently authenticated user."""
    photo_url = current_user.get("photo_url")
    if not photo_url and current_user.get("student_id"):
        s_doc = await db.students.find_one({"$or": [{"id": current_user["student_id"]}, {"roll_no": current_user["student_id"]}]})
        if s_doc:
            photo_url = s_doc.get("photo_url")

    return UserOut(
        id=str(current_user.get("_id", current_user.get("id", ""))),
        username=current_user["username"],
        role=current_user.get("role", "student"),
        student_id=current_user.get("student_id"),
        full_name=current_user.get("full_name"),
        photo_url=photo_url,
        is_active=current_user.get("is_active", True)
    )


@router.post("/token", response_model=Token)
async def token(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_database)):
    return await login(LoginRequest(username=form.username, password=form.password), db)

@router.post("/logout", status_code=204)
async def logout(user=Depends(get_current_user), db=Depends(get_database)):
    await db.users.update_one({"_id": user["_id"]}, {"$inc": {"token_version": 1}})
