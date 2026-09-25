import os
import secrets
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Central Fire Safety Institute (CFSI) API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment mode: 'development' or 'production'
    APP_ENV: str = "development"
    
    # JWT Settings
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48), validation_alias=AliasChoices("JWT_SECRET_KEY", "CFSI_JWT_SECRET"), min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    
    BOOTSTRAP_ADMIN_USERNAME: str = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin@cfsi.com")
    BOOTSTRAP_ADMIN_PASSWORD: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "Password@1")

    # MongoDB Database Settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "")
    
    # CORS Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://cfsi-fe.vercel.app",
        "*"
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"

    def model_post_init(self, __context):
        self.APP_ENV = (self.APP_ENV or "development").strip().lower()
        if not self.MONGODB_DB_NAME:
            self.MONGODB_DB_NAME = "cfsi_db" if self.APP_ENV == "production" else "cfsi_dev"

settings = Settings()
