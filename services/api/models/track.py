from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from database import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    title = Column(String(500), nullable=False)
    artist = Column(String(500), nullable=True, index=True)
    artist_id = Column(PGUUID(as_uuid=True), ForeignKey("artists.id", ondelete="SET NULL"), nullable=True, index=True)
    album = Column(String(500), nullable=True)
    album_id = Column(PGUUID(as_uuid=True), ForeignKey("albums.id", ondelete="SET NULL"), nullable=True, index=True)
    genre = Column(String(100), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    release_year = Column(Integer, nullable=True)
    isrc = Column(String(50), nullable=True)

    audio_url = Column(Text, nullable=True)
    cover_url = Column(Text, nullable=True)

    extra_metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="tracks")
    interactions = relationship("Interaction", back_populates="track")


# Pydantic schemas
class TrackBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    artist: Optional[str] = Field(None, max_length=500)
    album: Optional[str] = Field(None, max_length=500)
    genre: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=1)
    release_year: Optional[int] = Field(None, ge=1900, le=2100)


class TrackCreate(TrackBase):
    audio_url: Optional[str] = None
    cover_url: Optional[str] = None
    extra_metadata: dict = Field(default_factory=dict)


class TrackResponse(TrackBase):
    id: UUID
    audio_url: Optional[str]
    cover_url: Optional[str]
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrackUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    artist: Optional[str] = Field(None, max_length=500)
    album: Optional[str] = Field(None, max_length=500)
    genre: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=1)
    release_year: Optional[int] = Field(None, ge=1900, le=2100)
    audio_url: Optional[str] = None
    cover_url: Optional[str] = None
    extra_metadata: Optional[dict] = None