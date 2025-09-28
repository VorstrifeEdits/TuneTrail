from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, Text, CheckConstraint, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from enum import Enum

from database import Base


class SearchQuery(Base):
    """Search query logging for ML improvement."""
    __tablename__ = "search_queries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=False)
    filters = Column(JSON, default={})

    results_count = Column(Integer, default=0)
    clicked_result_id = Column(PGUUID(as_uuid=True), nullable=True)
    clicked_result_type = Column(String(50), nullable=True)
    clicked_position = Column(Integer, nullable=True)
    time_to_click_ms = Column(Integer, nullable=True)

    source = Column(String(50), nullable=True)
    device_type = Column(String(50), nullable=True)
    session_id = Column(PGUUID(as_uuid=True), nullable=True)

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class RecommendationImpression(Base):
    """Track which recommendations were shown to users."""
    __tablename__ = "recommendation_impressions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), index=True)

    recommendation_id = Column(PGUUID(as_uuid=True), nullable=True)
    model_type = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)
    recommendation_score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)

    position = Column(Integer, nullable=False)
    context_type = Column(String(50), nullable=True)
    context_id = Column(PGUUID(as_uuid=True), nullable=True)

    was_clicked = Column(Boolean, default=False, index=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    was_played = Column(Boolean, default=False)
    was_liked = Column(Boolean, default=False)
    was_saved = Column(Boolean, default=False)

    shown_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    time_visible_ms = Column(Integer, nullable=True)


class ContentView(Base):
    """View events for content without interaction."""
    __tablename__ = "content_views"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    content_type = Column(String(50), nullable=False, index=True)
    content_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)

    source = Column(String(50), nullable=True)
    source_id = Column(PGUUID(as_uuid=True), nullable=True)
    session_id = Column(PGUUID(as_uuid=True), nullable=True)

    time_spent_ms = Column(Integer, nullable=True)
    scrolled_to_bottom = Column(Boolean, default=False)

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint(
            "content_type IN ('track', 'album', 'artist', 'playlist', 'user_profile')",
            name="valid_content_type",
        ),
    )


class PlayerEvent(Base):
    """Granular player events for behavior analysis."""
    __tablename__ = "player_events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    session_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    position_ms = Column(Integer, nullable=True)

    seek_from_ms = Column(Integer, nullable=True)
    seek_to_ms = Column(Integer, nullable=True)

    buffer_duration_ms = Column(Integer, nullable=True)

    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    event_metadata = Column(JSON, default={})

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('seek', 'buffer_start', 'buffer_end', 'error', 'quality_change', 'volume_change', 'scrub')",
            name="valid_event_type",
        ),
    )


# Pydantic Schemas

class SearchQueryLog(BaseModel):
    """Log a search query with results."""
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field(..., pattern="^(all|track|playlist|artist|album)$")
    filters: dict = Field(default_factory=dict)
    results_count: int = Field(..., ge=0)
    session_id: Optional[UUID] = None
    device_type: Optional[str] = None


class SearchClick(BaseModel):
    """Record click on search result."""
    search_query_id: UUID
    clicked_result_id: UUID
    clicked_result_type: str = Field(..., pattern="^(track|playlist|artist|album)$")
    clicked_position: int = Field(..., ge=0)
    time_to_click_ms: int = Field(..., ge=0)


class ImpressionLog(BaseModel):
    """Log recommendation impressions."""
    track_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    model_type: str
    model_version: Optional[str] = None
    context_type: Optional[str] = None
    context_id: Optional[UUID] = None
    scores: Optional[List[float]] = None
    reasons: Optional[List[str]] = None


class ImpressionClick(BaseModel):
    """Record click on recommendation impression."""
    impression_id: UUID
    time_to_click_ms: int


class ViewEvent(BaseModel):
    """Log content view."""
    content_type: str = Field(..., pattern="^(track|album|artist|playlist|user_profile)$")
    content_id: UUID
    source: Optional[str] = Field(None, pattern="^(search|recommendations|browse|playlist|artist_page|album_page)$")
    source_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    time_spent_ms: Optional[int] = Field(None, ge=0)
    scrolled_to_bottom: bool = False


class PlayerEventLog(BaseModel):
    """Log granular player event."""
    event_type: str = Field(..., pattern="^(seek|buffer_start|buffer_end|error|quality_change|volume_change|scrub)$")
    track_id: UUID
    session_id: Optional[UUID] = None

    # Position in track
    position_ms: Optional[int] = Field(None, ge=0)

    # Seek events
    seek_from_ms: Optional[int] = Field(None, ge=0)
    seek_to_ms: Optional[int] = Field(None, ge=0)

    # Buffer events
    buffer_duration_ms: Optional[int] = Field(None, ge=0)

    # Error events
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Additional context
    event_metadata: dict = Field(default_factory=dict)