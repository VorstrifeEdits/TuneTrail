from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from enum import Enum

from database import Base


class RepeatMode(str, Enum):
    """Repeat modes for playback."""
    OFF = "off"
    TRACK = "track"
    CONTEXT = "context"


class PlayerState(Base):
    """
    Stores current playback state for each user/device.
    Enables cross-device sync and resume playback.
    """
    __tablename__ = "player_states"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, unique=True)

    is_playing = Column(Boolean, default=False)
    current_track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True)
    progress_ms = Column(Integer, default=0)

    shuffle_enabled = Column(Boolean, default=False)
    repeat_mode = Column(String(20), default="off")
    volume = Column(Integer, default=80)

    device_id = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)

    context_type = Column(String(50), nullable=True)
    context_id = Column(PGUUID(as_uuid=True), nullable=True)

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="player_state")
    current_track = relationship("Track", foreign_keys=[current_track_id])


class Queue(Base):
    """
    User's playback queue.
    Supports next up, play next, and queue management.
    """
    __tablename__ = "queues"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"))

    position = Column(Integer, nullable=False)
    is_priority = Column(Boolean, default=False)

    context_type = Column(String(50), nullable=True)
    context_id = Column(PGUUID(as_uuid=True), nullable=True)

    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="queue_items")
    track = relationship("Track")


class ListeningSession(Base):
    """
    Groups interactions into listening sessions.
    Critical for ML pattern detection.
    """
    __tablename__ = "listening_sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    device_type = Column(String(50))
    platform = Column(String(50))
    device_id = Column(String(255))

    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), default=datetime.utcnow)

    total_tracks_played = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)

    context_type = Column(String(50), nullable=True)
    context_id = Column(PGUUID(as_uuid=True), nullable=True)

    mood_tags = Column(JSON, default=[])
    activity_tags = Column(JSON, default=[])
    session_metadata = Column(JSON, default={})

    user = relationship("User", back_populates="listening_sessions")


class PlaybackStateResponse(BaseModel):
    """Current playback state."""
    is_playing: bool
    current_track: Optional["TrackResponse"] = None
    progress_ms: int
    duration_ms: Optional[int] = None

    shuffle_enabled: bool
    repeat_mode: RepeatMode
    volume: int

    device_id: Optional[str]
    device_name: Optional[str]
    device_type: Optional[str]

    context_type: Optional[str]
    context_id: Optional[UUID]

    timestamp: datetime

    class Config:
        from_attributes = True


class PlaybackAction(BaseModel):
    """Action to control playback."""
    device_id: Optional[str] = Field(None, description="Target device ID")


class PlayAction(BaseModel):
    """Start/resume playback with optional context."""
    track_ids: Optional[List[UUID]] = Field(None, description="Tracks to play")
    context_type: Optional[str] = Field(None, pattern="^(playlist|album|artist|radio)$")
    context_id: Optional[UUID] = Field(None, description="Playlist/album ID to play from")
    position_ms: int = Field(default=0, ge=0, description="Start position in milliseconds")
    device_id: Optional[str] = None


class SeekAction(BaseModel):
    """Seek to position in track."""
    position_ms: int = Field(..., ge=0, description="Position in milliseconds")


class VolumeAction(BaseModel):
    """Set volume."""
    volume: int = Field(..., ge=0, le=100, description="Volume level 0-100")


class QueueAddRequest(BaseModel):
    """Add tracks to queue."""
    track_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    play_next: bool = Field(
        default=False,
        description="Add to front of queue (play next) vs. end of queue",
    )
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None


class QueueItem(BaseModel):
    """Item in the queue."""
    id: UUID
    track: "TrackResponse"
    position: int
    is_priority: bool
    added_at: datetime
    context_type: Optional[str]
    context_id: Optional[UUID]

    class Config:
        from_attributes = True


class SessionStart(BaseModel):
    """Start a listening session."""
    device_type: str = Field(..., pattern="^(mobile|desktop|web|tablet|car|smart_speaker|tv)$")
    platform: str = Field(..., example="iOS")
    device_id: str = Field(..., example="device-12345")
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None


class SessionEnd(BaseModel):
    """End session data."""
    tracks_played: int = 0
    duration_seconds: int = 0


class SessionResponse(BaseModel):
    """Listening session details."""
    id: UUID
    device_type: str
    platform: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_tracks_played: int
    total_duration_seconds: int
    mood_tags: List[str] = []
    activity_tags: List[str] = []

    class Config:
        from_attributes = True


from models.track import TrackResponse
PlaybackStateResponse.model_rebuild()
QueueItem.model_rebuild()