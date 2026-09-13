from typing import Optional, List
from pydantic import BaseModel, Field

class AttendanceBase(BaseModel):
    id: Optional[str] = None
    student_id: str = Field(..., alias="studentId")
    roll_no: Optional[str] = Field(None, alias="rollNo")
    date: str
    slot: str  # 'Slot 1' | 'Slot 2' | 'Slot 3'
    course: str
    status: str  # 'Present' | 'Absent' | 'Late' | 'Leave'
    topic_or_module: Optional[str] = Field(None, alias="topicOrModule")
    remarks: Optional[str] = None
    marked_by: Optional[str] = Field(None, alias="markedBy")
    created_at: Optional[str] = Field(None, alias="createdAt")
    uploaded_at: Optional[str] = Field(None, alias="uploadedAt")
    is_locked: bool = Field(False, alias="isLocked")
    can_edit_until: Optional[str] = Field(None, alias="canEditUntil")

    class Config:
        populate_by_name = True
        from_attributes = True

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceUpdate(BaseModel):
    status: Optional[str] = None
    topic_or_module: Optional[str] = Field(None, alias="topicOrModule")
    remarks: Optional[str] = None
    marked_by: Optional[str] = Field(None, alias="markedBy")

    class Config:
        populate_by_name = True

class AttendanceBulkCreate(BaseModel):
    records: List[AttendanceCreate]

class AttendanceOut(AttendanceBase):
    id: str
