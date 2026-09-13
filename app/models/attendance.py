from sqlalchemy import Column, String, Index
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(String(100), primary_key=True, index=True)
    certificate_number = Column(String(100), index=True, nullable=False)
    date = Column(String(20), index=True, nullable=False)  # YYYY-MM-DD
    slot = Column(String(20), nullable=False)              # 'Slot 1', 'Slot 2', 'Slot 3'
    course = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False)            # 'Present', 'Absent', 'Late', 'Leave'
    topic_or_module = Column(String(255), nullable=True)
    remarks = Column(String(255), nullable=True)
    marked_by = Column(String(100), nullable=True)
    created_at = Column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_attendance_cert_date_slot", "certificate_number", "date", "slot"),
    )
