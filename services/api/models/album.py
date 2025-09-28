from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from database import Base


class Album(Base):
    """
    Music album aggregation.
    Automatically generated from track metadata or manually created.
    """
    __tablename__ = "albums"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    title = Column(String(500), nullable=False, index=True)
    artist = Column(String(500), nullable=True, index=True)
    release_year = Column(Integer, nullable=True)
    release_date = Column(DateTime(timezone=True), nullable=True)

    album_type = Column(String(50), nullable=True)
    total_tracks = Column(Integer, default=0)

    cover_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    genres = Column(JSON, default=[])
    labels = Column(JSON, default=[])
    external_ids = Column(JSON, default={})
    extra_metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="albums")
    tracks = relationship("Track", back_populates="album")
    saved_by_users = relationship("SavedAlbum", back_populates="album")


class Artist(Base):
    """
    Artist/band entity.
    Aggregates tracks and albums by artist.
    """
    __tablename__ = "artists"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    name = Column(String(500), nullable=False, unique=True, index=True)
    bio = Column(Text, nullable=True)

    image_url = Column(Text, nullable=True)
    banner_url = Column(Text, nullable=True)

    genres = Column(JSON, default=[])
    total_tracks = Column(Integer, default=0)
    total_albums = Column(Integer, default=0)
    total_followers = Column(Integer, default=0)

    external_ids = Column(JSON, default={})
    social_links = Column(JSON, default={})
    extra_metadata = Column(JSON, default={})

    verified = Column(Boolean, default=False)
    popularity_score = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="artists")
    followers = relationship("ArtistFollow", back_populates="artist")


class SavedAlbum(Base):
    """User's saved/liked albums."""
    __tablename__ = "saved_albums"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    album_id = Column(PGUUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    saved_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="saved_albums")
    album = relationship("Album", back_populates="saved_by_users")


class ArtistFollow(Base):
    """User following artists."""
    __tablename__ = "artist_follows"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    artist_id = Column(PGUUID(as_uuid=True), ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    followed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="followed_artists")
    artist = relationship("Artist", back_populates="followers")


class AlbumBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    artist: Optional[str] = Field(None, max_length=500)
    release_year: Optional[int] = Field(None, ge=1900, le=2100)
    album_type: Optional[str] = Field(None, pattern="^(album|single|compilation|ep)$")


class AlbumResponse(AlbumBase):
    id: UUID
    total_tracks: int
    cover_url: Optional[str]
    genres: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ArtistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    bio: Optional[str] = None


class ArtistResponse(ArtistBase):
    id: UUID
    image_url: Optional[str]
    genres: List[str] = []
    total_tracks: int
    total_albums: int
    total_followers: int
    verified: bool
    popularity_score: float

    class Config:
        from_attributes = True