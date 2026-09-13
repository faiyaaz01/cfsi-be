from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator
from typing import Literal

Role = Literal["admin", "teacher", "student"]

class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None  # 'admin' | 'student' | 'auto'

class UserOut(BaseModel):
    id: Union[str, int]
    username: str
    role: Role
    certificate_number: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True

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
    certificate_number: Optional[str] = None
    user_id: Optional[str] = None
    exp: Optional[int] = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9@._/+\-]+$")
    password: str = Field(min_length=8, max_length=72)
    role: Role
    full_name: str = Field(min_length=1, max_length=200)
    certificate_number: Optional[str] = None
    is_active: bool = True

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
    certificate_number: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        return UserCreate.password_bytes(value) if value is not None else value
