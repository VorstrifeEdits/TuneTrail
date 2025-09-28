from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Edition and Environment
    EDITION: str = "community"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str

    # Security
    JWT_SECRET: str
    API_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://tunetrail.app",
        "https://community.tunetrail.dev",
    ]

    # Storage
    STORAGE_TYPE: str = "minio"
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_REGION: str = "us-east-1"

    # ML Configuration
    MODEL_TIER: str = "basic"
    MAX_WORKERS: int = 4
    ENABLE_GPU: bool = False
    MODEL_CACHE_DIR: str = "/models"

    # Audio Processing
    FEATURE_EXTRACTION_BATCH_SIZE: int = 100
    AUDIO_SAMPLE_RATE: int = 22050
    MAX_AUDIO_LENGTH_SECONDS: int = 600

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True

    # Monitoring
    ENABLE_TELEMETRY: bool = False
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()