from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from enum import Enum

from database import Base


class InteractionType(str, Enum):
    """Types of user interactions with tracks."""
    PLAY = "play"
    SKIP = "skip"
    LIKE = "like"
    DISLIKE = "dislike"
    PLAYLIST_ADD = "playlist_add"
    SHARE = "share"


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), index=True)

    interaction_type = Column(String(50), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    play_duration_seconds = Column(Integer, nullable=True)
    context = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint(
            "interaction_type IN ('play', 'skip', 'like', 'dislike', 'playlist_add', 'share')",
            name="valid_interaction_type",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="valid_rating",
        ),
    )

    user = relationship("User", back_populates="interactions")
    track = relationship("Track", back_populates="interactions")


class InteractionCreate(BaseModel):
    track_id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    interaction_type: InteractionType = Field(..., example=InteractionType.PLAY)
    rating: Optional[int] = Field(None, ge=1, le=5, example=4, description="Rating from 1-5 stars")
    play_duration_seconds: Optional[int] = Field(
        None, ge=0, example=180, description="Duration of play in seconds"
    )

    session_id: Optional[UUID] = Field(None, description="Listening session ID (group related plays)")
    device_type: Optional[str] = Field(
        None,
        pattern="^(mobile|desktop|web|tablet|car|smart_speaker|tv)$",
        example="mobile",
        description="Device type",
    )
    platform: Optional[str] = Field(
        None,
        example="iOS",
        description="Platform: iOS, Android, Windows, Mac, Linux, Web",
    )
    source: Optional[str] = Field(
        None,
        pattern="^(playlist|search|recommendations|radio|artist_page|album_page|queue|library)$",
        example="playlist",
        description="Where was track played from",
    )
    source_id: Optional[UUID] = Field(None, description="ID of source playlist/recommendation")

    mood: Optional[str] = Field(
        None,
        pattern="^(happy|sad|energetic|calm|focused|relaxed|angry|romantic|melancholic)$",
        example="energetic",
        description="User's mood when playing",
    )
    activity: Optional[str] = Field(
        None,
        pattern="^(workout|study|sleep|commute|party|work|cooking|cleaning|relaxing)$",
        example="workout",
        description="User's activity",
    )
    skip_reason: Optional[str] = Field(
        None,
        pattern="^(dont_like|wrong_mood|heard_too_much|bad_quality|inappropriate|other)$",
        description="Why user skipped (if type=skip)",
    )

    shuffle_enabled: Optional[bool] = Field(None, description="Was shuffle on")
    repeat_mode: Optional[str] = Field(
        None, pattern="^(off|one|all)$", description="Repeat mode"
    )
    volume_level: Optional[int] = Field(None, ge=0, le=100, description="Volume level 0-100")

    context: dict = Field(
        default_factory=dict,
        example={"custom_field": "value"},
        description="Additional custom context",
    )


class InteractionResponse(BaseModel):
    id: UUID
    track_id: UUID
    interaction_type: InteractionType
    rating: Optional[int]
    play_duration_seconds: Optional[int]
    context: dict
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionStats(BaseModel):
    """Aggregate interaction statistics for a user."""
    total_plays: int
    total_likes: int
    total_skips: int
    unique_tracks_played: int
    total_play_time_hours: float
    favorite_genres: List[str] = []
    top_artists: List[str] = []


class TrackInteractionStats(BaseModel):
    """Aggregate interaction statistics for a track."""
    track_id: UUID
    total_plays: int
    total_likes: int
    total_skips: int
    average_rating: Optional[float]
    average_play_duration_seconds: Optional[float]
    unique_listeners: int