from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, index=True)
    cover_url = Column(Text, nullable=True)
    extra_metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="playlists")
    organization = relationship("Organization", back_populates="playlists")
    playlist_tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    playlist_id = Column(PGUUID(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    position = Column(Integer, nullable=False)
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    added_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    playlist = relationship("Playlist", back_populates="playlist_tracks")
    track = relationship("Track")
    user = relationship("User")


class PlaylistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="My Favorite Songs")
    description: Optional[str] = Field(None, max_length=5000, example="A collection of my all-time favorite tracks")
    is_public: bool = Field(default=False, example=False)
    cover_url: Optional[str] = Field(None, example="https://example.com/cover.jpg")


class PlaylistCreate(PlaylistBase):
    track_ids: List[UUID] = Field(default_factory=list, example=[])


class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    is_public: Optional[bool] = None
    cover_url: Optional[str] = None


class PlaylistTrackInfo(BaseModel):
    id: UUID
    title: str
    artist: Optional[str]
    duration_seconds: Optional[int]
    position: int
    added_at: datetime

    class Config:
        from_attributes = True


class PlaylistResponse(PlaylistBase):
    id: UUID
    user_id: UUID
    track_count: int = 0
    tracks: List[PlaylistTrackInfo] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlaylistSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    is_public: bool
    track_count: int
    cover_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddTracksToPlaylist(BaseModel):
    track_ids: List[UUID] = Field(..., min_items=1, example=["550e8400-e29b-41d4-a716-446655440000"])


class ReorderTracks(BaseModel):
    track_id: UUID
    new_position: int = Field(..., ge=0)