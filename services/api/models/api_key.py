from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
import secrets
import hashlib
from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, ARRAY, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator

from database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))

    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    scopes = Column(ARRAY(Text), default=[])
    permissions = Column(JSON, default={})

    environment = Column(String(50), default="production")

    rate_limit_requests_per_minute = Column(Integer, default=60)
    rate_limit_requests_per_hour = Column(Integer, default=1000)
    rate_limit_requests_per_day = Column(Integer, default=10000)

    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    ip_whitelist = Column(ARRAY(Text), nullable=True)
    user_agent_whitelist = Column(ARRAY(Text), nullable=True)
    metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_keys")
    organization = relationship("Organization", back_populates="api_keys")

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key.
        Returns: (full_key, key_hash, key_prefix)
        """
        prefix = "tt"
        random_part = secrets.token_urlsafe(32)
        full_key = f"{prefix}_{random_part}"

        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = f"{prefix}_{random_part[:8]}"

        return full_key, key_hash, key_prefix

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def is_valid(self) -> bool:
        """Check if the key is valid and not expired."""
        if not self.is_active:
            return False
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

    def has_scope(self, scope: str) -> bool:
        """Check if the key has a specific scope."""
        return scope in (self.scopes or [])

    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if the key has any of the specified scopes."""
        return any(scope in (self.scopes or []) for scope in scopes)

    def increment_usage(self) -> None:
        """Increment the usage counter and update last_used_at."""
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()


# Pydantic models for API

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    environment: str = Field(default="production")
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)

    rate_limit_requests_per_minute: int = Field(default=60, ge=1, le=10000)
    rate_limit_requests_per_hour: int = Field(default=1000, ge=1, le=100000)
    rate_limit_requests_per_day: int = Field(default=10000, ge=1, le=1000000)

    ip_whitelist: Optional[List[str]] = None
    metadata: dict = Field(default_factory=dict)

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    key_prefix: str
    scopes: List[str]
    environment: str

    rate_limit_requests_per_minute: int
    rate_limit_requests_per_hour: int
    rate_limit_requests_per_day: int

    total_requests: int
    last_used_at: Optional[datetime]

    is_active: bool
    expires_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyWithSecret(APIKeyResponse):
    """Only returned when creating a new key."""
    api_key: str

    class Config:
        from_attributes = True


class APIKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None

    rate_limit_requests_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_requests_per_hour: Optional[int] = Field(None, ge=1, le=100000)
    rate_limit_requests_per_day: Optional[int] = Field(None, ge=1, le=1000000)

    ip_whitelist: Optional[List[str]] = None
    metadata: Optional[dict] = None


class APIKeyUsageStats(BaseModel):
    api_key_id: UUID
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    requests_by_endpoint: dict
    requests_by_status_code: dict
    period_start: datetime
    period_end: datetime