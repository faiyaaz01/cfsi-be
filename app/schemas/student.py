from typing import Optional, List
from pydantic import BaseModel, Field

class StudentBase(BaseModel):
    id: str
    roll_no: str = Field(..., alias="rollNo")
    enrollment_no: Optional[str] = Field(None, alias="enrollmentNo")
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
    center_name: Optional[str] = Field(None, alias="centerName")
    mode: Optional[str] = Field("REGULAR", alias="mode")
    gender: Optional[str] = Field("MALE", alias="gender")
    photo_url: Optional[str] = Field(None, alias="photoUrl")
    mother_name: Optional[str] = Field(None, alias="motherName")
    birth_date: Optional[str] = Field(None, alias="birthDate")
    present_address: Optional[str] = Field(None, alias="presentAddress")
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    father_phone: Optional[str] = Field(None, alias="fatherPhone")
    mother_phone: Optional[str] = Field(None, alias="motherPhone")
    category: Optional[str] = Field(None, alias="category")
    aadhar_card: Optional[str] = Field(None, alias="aadharCard")
    email: Optional[str] = Field(None, alias="email")
    nationality: Optional[str] = Field("Indian", alias="nationality")
    state: Optional[str] = Field("Gujarat", alias="state")

    class Config:
        populate_by_name = True
        from_attributes = True

class StudentCreate(StudentBase):
    pass

class StudentOut(StudentBase):
    pass

class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    photo_url: Optional[str] = Field(None, alias="photoUrl")
    birth_date: Optional[str] = Field(None, alias="birthDate")
    gender: Optional[str] = Field(None, alias="gender")
    mother_name: Optional[str] = Field(None, alias="motherName")
    father_name: Optional[str] = Field(None, alias="fatherName")
    present_address: Optional[str] = Field(None, alias="presentAddress")
    student_phone: str = Field(..., alias="studentPhone", min_length=1)  # MANDATORY
    father_phone: Optional[str] = Field(None, alias="fatherPhone")
    mother_phone: Optional[str] = Field(None, alias="motherPhone")
    category: Optional[str] = Field(None, alias="category")
    aadhar_card: Optional[str] = Field(None, alias="aadharCard")
    email: Optional[str] = Field(None, alias="email")
    nationality: Optional[str] = Field("Indian", alias="nationality")
    state: Optional[str] = Field("Gujarat", alias="state")
    enrollment_no: Optional[str] = Field(None, alias="enrollmentNo")
    center_name: Optional[str] = Field(None, alias="centerName")
    center_location: Optional[str] = Field(None, alias="centerLocation")
    mode: Optional[str] = Field(None, alias="mode")

    class Config:
        populate_by_name = True

class BulkStudentImportItem(BaseModel):
    roll_no: Optional[str] = Field(None, alias="rollNo")
    student_id: Optional[str] = Field(None, alias="studentId")
    enrollment_no: Optional[str] = Field(None, alias="enrollmentNo")
    session_year: Optional[str] = Field(None, alias="sessionYear")
    name: str
    birth_date: str = Field(..., alias="birthDate")
    gender: Optional[str] = "MALE"
    course: Optional[str] = "Diploma In Fire Safety"
    batch: Optional[str] = "Batch 2026-2027"
    passing_year: Optional[str] = Field("2027", alias="passingYear")
    grade: Optional[str] = "Active Cadet"
    percentage: Optional[str] = "N/A"
    verification_status: Optional[str] = Field("Verified", alias="verificationStatus")
    issue_date: Optional[str] = Field("Ongoing", alias="issueDate")
    center_location: Optional[str] = Field("CFSI Vadodara Main Campus, Gujarat", alias="centerLocation")
    center_name: Optional[str] = Field(None, alias="centerName")
    mode: Optional[str] = Field("REGULAR", alias="mode")
    photo_url: Optional[str] = Field(None, alias="photoUrl")
    mother_name: Optional[str] = Field(None, alias="motherName")
    father_name: Optional[str] = Field(None, alias="fatherName")
    present_address: Optional[str] = Field(None, alias="presentAddress")
    student_phone: Optional[str] = Field(None, alias="studentPhone")
    father_phone: Optional[str] = Field(None, alias="fatherPhone")
    mother_phone: Optional[str] = Field(None, alias="motherPhone")
    category: Optional[str] = "General"
    aadhar_card: Optional[str] = Field(None, alias="aadharCard")
    email: Optional[str] = None
    nationality: Optional[str] = "Indian"
    state: Optional[str] = "Gujarat"

    class Config:
        populate_by_name = True

class BulkImportRequest(BaseModel):
    students: List[BulkStudentImportItem]
    default_batch: Optional[str] = "Batch 2026-2027"

class BulkImportStudentSummary(BaseModel):
    student_id: str
    roll_no: str
    enrollment_no: Optional[str] = None
    name: str
    birth_date: str
    generated_password: str
    status: str

class BulkImportResult(BaseModel):
    success: bool
    message: str
    total_processed: int
    created_count: int
    updated_count: int
    students: List[BulkImportStudentSummary]

class StudentVerifyResponse(BaseModel):
    verified: bool
    message: str
    student: Optional[StudentOut] = None
