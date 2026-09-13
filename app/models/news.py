from sqlalchemy import Column, String, Boolean, Text
from app.database import Base

class NewsPost(Base):
    __tablename__ = "news_posts"

    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    date = Column(String(20), nullable=False)
    excerpt = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    author = Column(String(100), nullable=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(String(50), nullable=True)
