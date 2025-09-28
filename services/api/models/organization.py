from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, Dict

from database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free", nullable=False)
    max_tracks = Column(Integer, default=1000)
    max_users = Column(Integer, default=1)
    features = Column(JSON, default={})
    metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    users = relationship("User", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")
    tracks = relationship("Track", back_populates="organization")


# Pydantic schemas
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="free")


class OrganizationCreate(OrganizationBase):
    max_tracks: int = Field(default=1000)
    max_users: int = Field(default=1)


class OrganizationResponse(OrganizationBase):
    id: str
    max_tracks: int
    max_users: int
    features: Dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True