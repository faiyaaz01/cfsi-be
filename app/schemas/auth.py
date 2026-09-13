from typing import Optional, Union
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None  # 'admin' | 'student' | 'auto'

class UserOut(BaseModel):
    id: Union[str, int]
    username: str
    role: str
    certificate_number: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True

    class Config:
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserOut

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    certificate_number: Optional[str] = None
    user_id: Optional[str] = None
    exp: Optional[int] = None
