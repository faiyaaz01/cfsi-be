from app.schemas.auth import LoginRequest, Token, TokenPayload, UserOut
from app.schemas.student import StudentBase, StudentCreate, StudentOut, StudentVerifyResponse
from app.schemas.attendance import AttendanceBase, AttendanceCreate, AttendanceUpdate, AttendanceBulkCreate, AttendanceOut
from app.schemas.news import NewsBase, NewsCreate, NewsUpdate, NewsOut

__all__ = [
    "LoginRequest", "Token", "TokenPayload", "UserOut",
    "StudentBase", "StudentCreate", "StudentOut", "StudentVerifyResponse",
    "AttendanceBase", "AttendanceCreate", "AttendanceUpdate", "AttendanceBulkCreate", "AttendanceOut",
    "NewsBase", "NewsCreate", "NewsUpdate", "NewsOut"
]
