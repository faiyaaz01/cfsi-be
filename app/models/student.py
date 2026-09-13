from sqlalchemy import Column, String, Integer
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(String(50), primary_key=True, index=True)
    roll_no = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    father_name = Column(String(200), nullable=False)
    course = Column(String(200), nullable=False)
    batch = Column(String(100), nullable=False)
    passing_year = Column(String(20), nullable=False)
    grade = Column(String(50), nullable=False)
    percentage = Column(String(20), nullable=False)
    verification_status = Column(String(50), default="Verified")
    issue_date = Column(String(100), nullable=False)
    center_location = Column(String(255), nullable=False)
    photo_url = Column(String(500), nullable=True)
