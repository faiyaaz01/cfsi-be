from datetime import timedelta
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
    Unified Login endpoint for Admin and Student accounts with MongoDB.
    Passwords verified via bcrypt against salted hashes.
    Issues JWT bearer token.
    """
    user = await db.users.find_one({"username": login_data.username})
    
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
        "certificate_number": user.get("certificate_number"),
        "user_id": user_id_str,
        "full_name": user.get("full_name")
    }
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    
    user_out = UserOut(
        id=user_id_str,
        username=user["username"],
        role=user_role,
        certificate_number=user.get("certificate_number"),
        full_name=user.get("full_name"),
        is_active=user.get("is_active", True)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user_role,
        user=user_out
    )

@router.get("/me", response_model=UserOut)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserOut(
        id=str(current_user.get("_id", current_user.get("id", ""))),
        username=current_user["username"],
        role=current_user.get("role", "student"),
        certificate_number=current_user.get("certificate_number"),
        full_name=current_user.get("full_name"),
        is_active=current_user.get("is_active", True)
    )
