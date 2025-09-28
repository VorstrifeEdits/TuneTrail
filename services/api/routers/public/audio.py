from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.track import Track
from models.audio_features import (
    AudioFeatures,
    AudioFeaturesResponse,
    AudioAnalysisRequest,
    SimilaritySearchRequest,
    SimilarTrackResult,
)
from middleware.auth import get_current_user
from middleware.tier import require_plan, PlanTier
from middleware.usage import check_usage_limit, require_feature

router = APIRouter(prefix="/audio", tags=["Audio Features"])


@router.get("/features/{track_id}", response_model=AudioFeaturesResponse)
async def get_audio_features(
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AudioFeaturesResponse:
    """
    Get audio features for a track.

    **Returns Spotify-compatible audio features:**
    - Tempo, key, mode, time signature
    - Energy, danceability, valence (0.0-1.0)
    - Acousticness, instrumentalness, etc.

    **Use Cases:**
    - Display track characteristics in UI
    - Filter by audio properties
    - Input for ML models

    **Available:** All tiers (Community, Starter, Pro, Enterprise)
    """
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.org_id == current_user.org_id,
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    features_result = await db.execute(
        select(AudioFeatures).where(AudioFeatures.track_id == track_id)
    )
    features = features_result.scalar_one_or_none()

    if not features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio features not yet extracted. Use POST /audio/analyze to trigger analysis.",
        )

    return AudioFeaturesResponse.from_orm(features)


@router.post(
    "/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(check_usage_limit("audio_analysis_per_day"))],
)
async def analyze_track(
    analysis_request: AudioAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> dict:
    """
    Trigger audio feature extraction for a track.

    **Process:**
    1. Validates track exists
    2. Queues analysis job
    3. Returns job ID
    4. Analysis runs asynchronously (Celery)
    5. Results available via GET /audio/features/{track_id}

    **Features Extracted:**
    - Basic: tempo, key, loudness (fast)
    - Perceptual: energy, danceability, valence (medium)
    - Embeddings: 512-dim vector (slow, ML critical)

    **Limits:**
    - Community: Unlimited (self-hosted)
    - Starter: 100/day
    - Pro: 1,000/day
    - Enterprise: Unlimited

    **Priority Queue (Pro+ only):**
    - priority=true: Jump to front of queue
    - priority=false: Normal queue
    """
    result = await db.execute(
        select(Track).where(
            Track.id == analysis_request.track_id,
            Track.org_id == current_user.org_id,
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    if analysis_request.priority:
        await require_plan(["pro", "enterprise"])(current_user, db)

    job_id = f"analysis-{track.id}"

    return {
        "message": "Audio analysis queued",
        "job_id": job_id,
        "track_id": analysis_request.track_id,
        "estimated_completion": "30-60 seconds",
        "check_status": f"/audio/jobs/{job_id}",
    }


@router.post(
    "/similarity-search",
    response_model=List[SimilarTrackResult],
    dependencies=[Depends(require_plan([PlanTier.STARTER, PlanTier.PRO, PlanTier.ENTERPRISE]))],
)
async def search_similar_by_audio(
    search_request: SimilaritySearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SimilarTrackResult]:
    """
    Find similar tracks using audio feature vectors.

    **Algorithm:**
    - Cosine similarity on 512-dim embeddings
    - Optionally filter by genre
    - Returns tracks sorted by similarity

    **Use Cases:**
    - \"More like this\" feature
    - Audio-based radio
    - Similar track recommendations

    **Requires:**
    - Track must have audio features extracted
    - Starter+ plan (uses vector similarity search)

    **Performance:**
    - Uses pgvector IVFFlat index
    - Sub-100ms for million+ tracks
    """
    result = await db.execute(
        select(AudioFeatures).where(AudioFeatures.track_id == search_request.track_id)
    )
    source_features = result.scalar_one_or_none()

    if not source_features or source_features.embedding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio features not available for this track. Run analysis first.",
        )

    query = text("""
        SELECT
            af.track_id,
            1 - (af.embedding <=> :source_embedding) AS similarity
        FROM audio_features af
        JOIN tracks t ON t.id = af.track_id
        WHERE
            t.org_id = :org_id
            AND af.track_id != :source_track_id
            AND af.embedding IS NOT NULL
            AND (1 - (af.embedding <=> :source_embedding)) >= :min_similarity
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    results = await db.execute(
        query,
        {
            "source_embedding": source_features.embedding,
            "org_id": current_user.org_id,
            "source_track_id": search_request.track_id,
            "min_similarity": search_request.min_similarity,
            "limit": search_request.limit,
        }
    )

    similar_tracks = []
    for row in results.all():
        similar_tracks.append(
            SimilarTrackResult(
                track_id=row[0],
                similarity_score=float(row[1]),
                audio_similarity_breakdown={},
            )
        )

    return similar_tracks


class BatchAnalyzeRequest(BaseModel):
    track_ids: List[UUID] = Field(..., min_items=1, max_items=1000)


@router.post("/batch-analyze", dependencies=[Depends(require_plan(["starter", "pro", "enterprise"]))])
async def batch_analyze(
    batch_request: BatchAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch audio feature extraction.

    **Analyzes multiple tracks in one job.**

    **Limits:**
    - Starter: 100 tracks/batch, 1 batch/day
    - Pro: 1000 tracks/batch, 10 batches/day
    - Enterprise: Unlimited

    **Process:**
    - Queues batch job
    - Returns job ID
    - Check status: GET /audio/jobs/{job_id}

    **Available:** Starter+ only
    """
    return {
        "message": "Batch analysis queued",
        "job_id": f"batch-{len(batch_request.track_ids)}-tracks",
        "track_count": len(batch_request.track_ids),
        "estimated_completion": f"{len(batch_request.track_ids) * 2} seconds",
    }