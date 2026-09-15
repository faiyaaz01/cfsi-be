from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CourseBase(BaseModel):
    id: Optional[str] = None
    title: str
    slug: str
    duration: str
    eligibility: str
    fee: str
    fee_number: int = Field(0, alias="feeNumber")
    badge: Optional[str] = None
    icon: str = "Flame"
    short_description: str = Field(..., alias="shortDescription")
    full_description: str = Field("", alias="fullDescription")
    syllabus: List[str] = []
    physical_requirements: List[str] = Field(default_factory=list, alias="physicalRequirements")
    career_opportunities: List[str] = Field(default_factory=list, alias="careerOpportunities")
    certification_body: str = Field("", alias="certificationBody")

    class Config:
        populate_by_name = True
        from_attributes = True

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    duration: Optional[str] = None
    eligibility: Optional[str] = None
    fee: Optional[str] = None
    fee_number: Optional[int] = Field(None, alias="feeNumber")
    badge: Optional[str] = None
    icon: Optional[str] = None
    short_description: Optional[str] = Field(None, alias="shortDescription")
    full_description: Optional[str] = Field(None, alias="fullDescription")
    syllabus: Optional[List[str]] = None
    physical_requirements: Optional[List[str]] = Field(None, alias="physicalRequirements")
    career_opportunities: Optional[List[str]] = Field(None, alias="careerOpportunities")
    certification_body: Optional[str] = Field(None, alias="certificationBody")

    class Config:
        populate_by_name = True

class CourseOut(CourseBase):
    id: str

class TrainingDrillBase(BaseModel):
    id: Optional[str] = None
    title: str
    tag: str = "Drill"
    duration: str = "Practical"
    image: str
    description: str = ""
    highlights: List[str] = []
    equipment_used: List[str] = Field(default_factory=list, alias="equipmentUsed")

    class Config:
        populate_by_name = True
        from_attributes = True

class TrainingDrillCreate(TrainingDrillBase):
    pass

class TrainingDrillUpdate(BaseModel):
    title: Optional[str] = None
    tag: Optional[str] = None
    duration: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None
    equipment_used: Optional[List[str]] = Field(None, alias="equipmentUsed")

    class Config:
        populate_by_name = True

class TrainingDrillOut(TrainingDrillBase):
    id: str

class GalleryPhotoBase(BaseModel):
    id: Optional[str] = None
    title: str
    category: str = "Training"
    image_url: str = Field(..., alias="imageUrl")
    caption: str = ""
    date: str = ""

    class Config:
        populate_by_name = True
        from_attributes = True

class GalleryPhotoCreate(GalleryPhotoBase):
    pass

class GalleryPhotoUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = Field(None, alias="imageUrl")
    caption: Optional[str] = None
    date: Optional[str] = None

    class Config:
        populate_by_name = True

class GalleryPhotoOut(GalleryPhotoBase):
    id: str

class GalleryVideoBase(BaseModel):
    id: Optional[str] = None
    youtube_id: str = Field(..., alias="youtubeId")
    title: str
    category: str = "Practical Drill"
    duration: str = "3:00"
    description: str = ""

    class Config:
        populate_by_name = True
        from_attributes = True

class GalleryVideoCreate(GalleryVideoBase):
    pass

class GalleryVideoUpdate(BaseModel):
    youtube_id: Optional[str] = Field(None, alias="youtubeId")
    title: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None

    class Config:
        populate_by_name = True

class GalleryVideoOut(GalleryVideoBase):
    id: str

class DisplaySettingsSchema(BaseModel):
    heroNoticeBanner: bool = True
    newsTickerMarquee: bool = True
    coursesSection: bool = True
    groundTrainingSection: bool = True
    photoGallerySection: bool = True
    videoGallerySection: bool = True
    studentVerificationBox: bool = True
    placementStatsBar: bool = True
    admissionInquiryModal: bool = True
    attendanceSystem: bool = True
    studentPortalLogin: bool = True
    institutePortalLogin: bool = True
    bulkStudentUpload: bool = True
    maintenanceModeBanner: bool = False

    class Config:
        populate_by_name = True
