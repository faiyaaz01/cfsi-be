from sqlalchemy import Column, String, Float
from app.database import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(String(100), primary_key=True, index=True)
    certificate_number = Column(String(100), index=True, nullable=False)
    course = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False, default=100.0)
    grade = Column(String(20), nullable=False)
    exam_date = Column(String(20), nullable=False)
    semester_or_term = Column(String(100), nullable=False)
    remarks = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=True)
