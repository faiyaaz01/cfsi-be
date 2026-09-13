from typing import Optional
from pydantic import BaseModel, Field

class StudentBase(BaseModel):
    id: str
    certificate_number: str = Field(..., alias="certificateNumber")
    roll_no: str = Field(..., alias="rollNo")
    name: str
    father_name: str = Field(..., alias="fatherName")
    course: str
    batch: str
    passing_year: str = Field(..., alias="passingYear")
    grade: str
    percentage: str
    verification_status: str = Field(default="Verified", alias="verificationStatus")
    issue_date: str = Field(..., alias="issueDate")
    center_location: str = Field(..., alias="centerLocation")
    photo_url: Optional[str] = Field(None, alias="photoUrl")

    class Config:
        populate_by_name = True
        from_attributes = True

class StudentCreate(StudentBase):
    pass

class StudentOut(StudentBase):
    pass

class StudentVerifyResponse(BaseModel):
    verified: bool
    message: str
    student: Optional[StudentOut] = None
