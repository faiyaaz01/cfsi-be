from typing import Optional, List
from pydantic import BaseModel, Field

class AttendanceBase(BaseModel):
    id: Optional[str] = None
    certificate_number: str = Field(..., alias="certificateNumber")
    date: str
    slot: str  # 'Slot 1' | 'Slot 2' | 'Slot 3'
    course: str
    status: str  # 'Present' | 'Absent' | 'Late' | 'Leave'
    topic_or_module: Optional[str] = Field(None, alias="topicOrModule")
    remarks: Optional[str] = None
    marked_by: Optional[str] = Field(None, alias="markedBy")
    created_at: Optional[str] = Field(None, alias="createdAt")

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
