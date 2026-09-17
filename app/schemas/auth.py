from typing import Optional, Union, List
from pydantic import BaseModel, Field, field_validator
from typing import Literal

Role = Literal["admin", "teacher", "student", "leader"]

class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None  # 'admin' | 'student' | 'teacher' | 'leader' | 'auto'

class UserOut(BaseModel):
    id: Union[str, int]
    username: str
    role: Role
    student_id: Optional[str] = None
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True
    assigned_modules: Optional[List[str]] = Field(default_factory=list)
    assigned_slots: Optional[List[str]] = Field(default_factory=list)

    class Config:
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user: UserOut

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    student_id: Optional[str] = None
    user_id: Optional[str] = None
    exp: Optional[int] = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9@._/+\-]+$")
    password: str = Field(min_length=8, max_length=72)
    role: Role
    full_name: str = Field(min_length=1, max_length=200)
    student_id: Optional[str] = None
    is_active: bool = True
    assigned_modules: Optional[List[str]] = Field(default_factory=list)
    assigned_slots: Optional[List[str]] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value

class UserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    role: Optional[Role] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    student_id: Optional[str] = None
    is_active: Optional[bool] = None
    assigned_modules: Optional[List[str]] = None
    assigned_slots: Optional[List[str]] = None

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        return UserCreate.password_bytes(value) if value is not None else value
