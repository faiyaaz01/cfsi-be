from typing import Optional
from pydantic import BaseModel, Field

class ResultBase(BaseModel):
    id: Optional[str] = None
    certificate_number: str = Field(..., alias="certificateNumber")
    course: str
    subject: str
    marks_obtained: float = Field(..., alias="marksObtained")
    max_marks: float = Field(100.0, alias="maxMarks")
    grade: str
    exam_date: str = Field(..., alias="examDate")
    semester_or_term: str = Field(..., alias="semesterOrTerm")
    remarks: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True

class ResultCreate(ResultBase):
    pass

class ResultUpdate(BaseModel):
    course: Optional[str] = None
    subject: Optional[str] = None
    marks_obtained: Optional[float] = Field(None, alias="marksObtained")
    max_marks: Optional[float] = Field(None, alias="maxMarks")
    grade: Optional[str] = None
    exam_date: Optional[str] = Field(None, alias="examDate")
    semester_or_term: Optional[str] = Field(None, alias="semesterOrTerm")
    remarks: Optional[str] = None

    class Config:
        populate_by_name = True

class ResultOut(ResultBase):
    id: str
