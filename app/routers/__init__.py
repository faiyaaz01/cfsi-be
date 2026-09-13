from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.attendance import router as attendance_router
from app.routers.news import router as news_router

__all__ = [
    "auth_router",
    "students_router",
    "attendance_router",
    "news_router"
]
