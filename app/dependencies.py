from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    username: Optional[str] = payload.get("sub")
    if not username:
        raise credentials_exception
    
    user = await db.users.find_one({"username": username, "is_active": True})
    if not user or payload.get("user_id") != str(user["_id"]) or payload.get("token_version", 0) != user.get("token_version", 0):
        raise credentials_exception
    
    # Normalize ID to string
    user["id"] = str(user.get("_id", user.get("id", "")))
    return user

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    return await get_current_user(token, db)

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation"
        )
    return current_user

async def require_student(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required for this operation"
        )
    return current_user


async def require_staff(current_user=Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "teacher", "leader"):
        raise HTTPException(status_code=403, detail="Admin, Teacher, or Leader access required")
    return current_user
