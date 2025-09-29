from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.track import Track, TrackResponse
from models.interaction import Interaction
from middleware.auth import get_current_user
from services.ml_client import ml_client

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RecommendationParams(BaseModel):
    """Parameters for generating recommendations."""
    limit: int = Field(default=20, ge=1, le=100, description="Number of recommendations to return")
    genres: Optional[List[str]] = Field(None, description="Filter by genres")
    exclude_listened: bool = Field(default=True, description="Exclude already played tracks")
    model_type: str = Field(default="content_based", description="Recommendation algorithm")


class RecommendationResponse(BaseModel):
    """A single recommendation with score and reasoning."""
    track: TrackResponse
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence score")
    reason: str = Field(..., description="Why this track was recommended")
    model_used: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Number of recommendations"),
    genres: Optional[str] = Query(None, description="Comma-separated genres to filter"),
    exclude_listened: bool = Query(True, description="Exclude previously played tracks"),
) -> List[RecommendationResponse]:
    """
    Get personalized music recommendations.

    **Enhanced with ML Engine Integration:**
    - Free: Collaborative filtering + popularity + genre-based
    - Starter: + Content-based filtering (audio similarity)
    - Pro: + Neural collaborative filtering + deep learning
    - Enterprise: + Custom model training

    **Models Used:**
    - Free Tier: ALS collaborative filtering, time-decayed popularity
    - Starter Tier: FAISS audio similarity, daily mix generation
    - Pro Tier: Neural CF (PyTorch), deep taste profiling
    - Enterprise Tier: Custom model training

    **Required scopes**: `read:recommendations`
    """
    # Prepare filters
    filters = {}
    if genres:
        filters['genres'] = genres.split(",")

    # Prepare context
    context = {
        'exclude_listened': exclude_listened,
        'timestamp': datetime.utcnow().isoformat(),
        'request_source': 'api_recommendations_endpoint'
    }

    # Try ML engine first
    ml_recommendations = await ml_client.get_recommendations(
        user_id=current_user.id,
        user=current_user,
        limit=limit,
        filters=filters,
        context=context
    )

    # If ML engine returns recommendations, convert them
    if ml_recommendations:
        recommendations = []
        for ml_rec in ml_recommendations:
            # Get track data from database
            track_result = await db.execute(
                select(Track).where(Track.id == UUID(ml_rec['track_id']))
            )
            track = track_result.scalar_one_or_none()

            if track:
                recommendations.append(
                    RecommendationResponse(
                        track=TrackResponse.from_orm(track),
                        score=ml_rec['score'],
                        reason=ml_rec['reason'],
                        model_used=ml_rec['model_used'],
                    )
                )

        if recommendations:
            return recommendations

    # Fallback to simple algorithm if ML engine unavailable
    genre_list = genres.split(",") if genres else None

    listened_track_ids = set()
    if exclude_listened:
        listened_query = select(Interaction.track_id).where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type.in_(["play", "like"]),
        )
        result = await db.execute(listened_query)
        listened_track_ids = {row[0] for row in result.all()}

    user_top_genres_query = (
        select(Track.genre, func.count(Interaction.id).label("count"))
        .join(Interaction, Interaction.track_id == Track.id)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == "play",
            Track.genre.isnot(None),
        )
        .group_by(Track.genre)
        .order_by(func.count(Interaction.id).desc())
        .limit(5)
    )
    genres_result = await db.execute(user_top_genres_query)
    user_favorite_genres = [row[0] for row in genres_result.all()]

    query = select(Track).where(Track.org_id == current_user.org_id)

    if listened_track_ids:
        query = query.where(Track.id.notin_(listened_track_ids))

    if genre_list:
        query = query.where(Track.genre.in_(genre_list))
    elif user_favorite_genres:
        query = query.where(Track.genre.in_(user_favorite_genres))

    query = query.order_by(Track.created_at.desc()).limit(limit)

    result = await db.execute(query)
    recommended_tracks = result.scalars().all()

    recommendations = []
    for track in recommended_tracks:
        score = 0.7 if track.genre in user_favorite_genres else 0.5

        if track.genre in user_favorite_genres:
            reason = f"Popular in your favorite genre: {track.genre}"
        else:
            reason = "New addition to the library"

        recommendations.append(
            RecommendationResponse(
                track=TrackResponse.from_orm(track),
                score=score,
                reason=reason,
                model_used="fallback_genre_based_v1",
            )
        )

    return recommendations


@router.get("/similar/{track_id}", response_model=List[RecommendationResponse])
async def get_similar_tracks(
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="Number of similar tracks"),
) -> List[RecommendationResponse]:
    """
    Get tracks similar to a specific track.

    **Enhanced with ML Engine Integration:**
    - Free: Basic genre + artist similarity
    - Starter+: Audio feature similarity (FAISS vector search)
    - Pro+: Deep audio embeddings + collaborative patterns

    **Algorithm:**
    - Starter+: 512-dimensional audio embedding cosine similarity
    - Uses FAISS for fast nearest neighbor search
    - Fallback to genre/artist matching if ML unavailable

    **Required scopes**: `read:recommendations`
    """
    # Verify track exists
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.org_id == current_user.org_id,
        )
    )
    source_track = result.scalar_one_or_none()

    if not source_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    # Try ML engine first
    ml_similar = await ml_client.get_similar_tracks(
        track_id=track_id,
        user=current_user,
        limit=limit
    )

    # If ML engine returns results, convert them
    if ml_similar:
        recommendations = []
        for ml_rec in ml_similar:
            # Get track data from database
            track_result = await db.execute(
                select(Track).where(Track.id == UUID(ml_rec['track_id']))
            )
            track = track_result.scalar_one_or_none()

            if track:
                recommendations.append(
                    RecommendationResponse(
                        track=TrackResponse.from_orm(track),
                        score=ml_rec['score'],
                        reason=ml_rec['reason'],
                        model_used=ml_rec['model_used'],
                    )
                )

        if recommendations:
            return recommendations

    # Fallback to simple similarity if ML engine unavailable
    query = (
        select(Track)
        .where(
            Track.org_id == current_user.org_id,
            Track.id != track_id,
        )
    )

    filters = []
    if source_track.genre:
        filters.append(Track.genre == source_track.genre)
    if source_track.artist:
        filters.append(Track.artist == source_track.artist)

    if filters:
        query = query.where(or_(*filters))

    query = query.limit(limit)

    result = await db.execute(query)
    similar_tracks = result.scalars().all()

    recommendations = []
    for track in similar_tracks:
        if track.genre == source_track.genre and track.artist == source_track.artist:
            score = 0.95
            reason = f"Same artist and genre as '{source_track.title}'"
        elif track.genre == source_track.genre:
            score = 0.85
            reason = f"Similar genre: {track.genre}"
        elif track.artist == source_track.artist:
            score = 0.80
            reason = f"Same artist: {track.artist}"
        else:
            score = 0.60
            reason = "Similar characteristics"

        recommendations.append(
            RecommendationResponse(
                track=TrackResponse.from_orm(track),
                score=score,
                reason=reason,
                model_used="fallback_similarity_v1",
            )
        )

    recommendations.sort(key=lambda x: x.score, reverse=True)

    return recommendations