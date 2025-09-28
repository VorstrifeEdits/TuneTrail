from datetime import datetime
from uuid import UUID
from typing import Optional, List
from sqlalchemy import Column, Float, Integer, DateTime, String, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from database import Base


class AudioFeatures(Base):
    """
    Audio features extracted from tracks.

    **Critical for ML recommendations:**
    - Content-based filtering
    - Audio similarity search
    - Mood detection
    - Context matching (workout, study, etc.)
    """
    __tablename__ = "audio_features"

    track_id = Column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True)

    # Basic audio properties
    tempo = Column(Float, nullable=True)
    beats_per_minute = Column(Float, nullable=True)
    key = Column(Integer, nullable=True)
    mode = Column(Integer, nullable=True)
    time_signature = Column(Integer, nullable=True)
    loudness = Column(Float, nullable=True)

    # Perceptual features (0.0-1.0 range, like Spotify)
    energy = Column(Float, nullable=True, index=True)
    danceability = Column(Float, nullable=True, index=True)
    valence = Column(Float, nullable=True, index=True)
    acousticness = Column(Float, nullable=True)
    instrumentalness = Column(Float, nullable=True)
    liveness = Column(Float, nullable=True)
    speechiness = Column(Float, nullable=True)

    # Spectral features
    spectral_centroid = Column(Float, nullable=True)
    spectral_bandwidth = Column(Float, nullable=True)
    spectral_rolloff = Column(Float, nullable=True)
    zero_crossing_rate = Column(Float, nullable=True)

    # Rhythm features
    rhythm_strength = Column(Float, nullable=True)

    # Harmonic features
    harmonicity = Column(Float, nullable=True)
    chroma_features = Column(ARRAY(Float), nullable=True)

    # ML embeddings (512-dimensional vector for similarity search)
    embedding = Column(Vector(512), nullable=True)

    # MFCC features (20 coefficients)
    mfcc_features = Column(ARRAY(Float), nullable=True)

    # Metadata
    extraction_version = Column(String(50), nullable=True)
    extracted_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationship
    track = relationship("Track", back_populates="audio_features")


class AudioFeaturesResponse(BaseModel):
    """Audio features response (Spotify-compatible format)."""
    track_id: UUID

    # Timing
    tempo: Optional[float] = Field(None, description="BPM")
    time_signature: Optional[int] = Field(None, description="e.g., 4 for 4/4 time")

    # Musical
    key: Optional[int] = Field(None, ge=0, le=11, description="Pitch class (0=C, 1=C#, etc.)")
    mode: Optional[int] = Field(None, ge=0, le=1, description="0=minor, 1=major")
    loudness: Optional[float] = Field(None, description="Overall loudness in dB")

    # Perceptual (0.0-1.0)
    energy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Intensity and activity")
    danceability: Optional[float] = Field(None, ge=0.0, le=1.0, description="How suitable for dancing")
    valence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Musical positiveness (happy vs. sad)")
    acousticness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Acoustic vs. electronic")
    instrumentalness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vocals vs. instrumental")
    liveness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Live recording likelihood")
    speechiness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Spoken words vs. music")

    # Advanced (for ML)
    spectral_centroid: Optional[float] = None
    rhythm_strength: Optional[float] = None

    extraction_version: Optional[str] = None
    extracted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AudioAnalysisRequest(BaseModel):
    """Request audio analysis for a track."""
    track_id: UUID
    priority: bool = Field(default=False, description="High priority (Pro+ feature)")
    extract_embeddings: bool = Field(default=True, description="Extract ML embeddings (slower)")


class SimilaritySearchRequest(BaseModel):
    """Search for similar tracks by audio features."""
    track_id: UUID
    limit: int = Field(default=20, ge=1, le=100)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum cosine similarity")
    filter_by_genre: bool = Field(default=False, description="Limit to same genre")


class SimilarTrackResult(BaseModel):
    """Similar track with similarity score."""
    track_id: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity (1.0 = identical)")
    audio_similarity_breakdown: dict = Field(
        default_factory=dict,
        example={
            "tempo_match": 0.95,
            "key_match": 1.0,
            "energy_match": 0.88,
            "overall": 0.91
        }
    )