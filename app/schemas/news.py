from typing import Optional
from pydantic import BaseModel, Field

class NewsBase(BaseModel):
    id: Optional[str] = None
    title: str
    category: str
    date: str
    excerpt: str
    content: str
    image_url: Optional[str] = Field(None, alias="imageUrl")
    author: str
    is_pinned: bool = Field(False, alias="isPinned")
    created_at: Optional[str] = Field(None, alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True

class NewsCreate(NewsBase):
    pass

class NewsUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = Field(None, alias="imageUrl")
    author: Optional[str] = None
    is_pinned: Optional[bool] = Field(None, alias="isPinned")

    class Config:
        populate_by_name = True

class NewsOut(NewsBase):
    id: str
