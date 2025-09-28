from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.track import Track, TrackResponse
from models.interaction import Interaction
from middleware.auth import get_current_user

router = APIRouter(prefix="/browse", tags=["Browse & Discovery"])


class GenreInfo(BaseModel):
    """Genre with metadata."""
    name: str
    track_count: int
    description: Optional[str] = None
    cover_url: Optional[str] = None


class TrendingTrack(BaseModel):
    """Trending track with popularity metrics."""
    track: TrackResponse
    play_count: int
    like_count: int
    trend_score: float

    class Config:
        from_attributes = True


@router.get("/genres", response_model=List[GenreInfo])
async def browse_genres(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GenreInfo]:
    """
    Browse all available genres.

    Returns all genres in the library with track counts.

    **Use Cases:**
    - Genre discovery
    - Browse by mood/style
    - Filter recommendations by genre

    **Required scopes**: `read:tracks`
    """
    query = (
        select(Track.genre, func.count(Track.id).label("count"))
        .where(
            Track.org_id == current_user.org_id,
            Track.genre.isnot(None),
        )
        .group_by(Track.genre)
        .order_by(func.count(Track.id).desc())
    )

    result = await db.execute(query)
    genres = [
        GenreInfo(name=row[0], track_count=row[1]) for row in result.all()
    ]

    return genres


@router.get("/genres/{genre}/tracks", response_model=List[TrackResponse])
async def browse_genre_tracks(
    genre: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
) -> List[TrackResponse]:
    """
    Get tracks in a specific genre.

    Returns tracks ordered by popularity (play count).

    **Required scopes**: `read:tracks`
    """
    query = (
        select(Track)
        .where(
            Track.org_id == current_user.org_id,
            Track.genre == genre,
        )
        .order_by(Track.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in tracks]


@router.get("/new-releases", response_model=List[TrackResponse])
async def browse_new_releases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(30, ge=1, le=365, description="How recent (days)"),
) -> List[TrackResponse]:
    """
    Get recently added tracks.

    Returns newest additions to the library.

    **Use Cases:**
    - Discover new music
    - "What's New" section
    - New release notifications

    **Required scopes**: `read:tracks`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Track)
        .where(
            Track.org_id == current_user.org_id,
            Track.created_at >= cutoff_date,
        )
        .order_by(Track.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in tracks]


@router.get("/trending", response_model=List[TrendingTrack])
async def browse_trending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(7, ge=1, le=90, description="Trending period (days)"),
) -> List[TrendingTrack]:
    """
    Get trending tracks.

    Returns tracks with highest engagement (plays + likes) in the recent period.

    **Trending Algorithm:**
    - Play count in last N days
    - Like count
    - Weighted by recency (more recent = higher weight)
    - Normalized by track age

    **Use Cases:**
    - "Trending Now" section
    - Popular music discovery
    - Social proof

    **Required scopes**: `read:tracks`, `read:interactions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    trending_query = (
        select(
            Track,
            func.count(
                func.case((Interaction.interaction_type == "play", 1))
            ).label("play_count"),
            func.count(
                func.case((Interaction.interaction_type == "like", 1))
            ).label("like_count"),
        )
        .outerjoin(Interaction, Interaction.track_id == Track.id)
        .where(
            Track.org_id == current_user.org_id,
            or_(
                Interaction.created_at >= cutoff_date,
                Interaction.created_at.is_(None),
            ),
        )
        .group_by(Track.id)
        .having(func.count(Interaction.id) > 0)
        .order_by(
            (
                func.count(func.case((Interaction.interaction_type == "play", 1))) * 1.0
                + func.count(func.case((Interaction.interaction_type == "like", 1))) * 2.0
            ).desc()
        )
        .limit(limit)
    )

    result = await db.execute(trending_query)
    rows = result.all()

    trending = []
    for track, play_count, like_count in rows:
        trend_score = (play_count * 1.0 + like_count * 2.0) / max((play_count + like_count), 1)

        trending.append(
            TrendingTrack(
                track=TrackResponse.from_orm(track),
                play_count=play_count,
                like_count=like_count,
                trend_score=min(trend_score, 1.0),
            )
        )

    return trending


@router.get("/popular", response_model=List[TrackResponse])
async def browse_popular(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> List[TrackResponse]:
    """
    Get all-time popular tracks.

    Returns tracks with highest total play counts (all time).

    **Different from Trending:**
    - Trending: Recent activity only
    - Popular: All-time cumulative

    **Required scopes**: `read:tracks`, `read:interactions`
    """
    popular_query = (
        select(Track, func.count(Interaction.id).label("interaction_count"))
        .outerjoin(Interaction, Interaction.track_id == Track.id)
        .where(
            Track.org_id == current_user.org_id,
            Interaction.interaction_type == "play",
        )
        .group_by(Track.id)
        .order_by(func.count(Interaction.id).desc())
        .limit(limit)
    )

    result = await db.execute(popular_query)
    popular_tracks = [row[0] for row in result.all()]

    return [TrackResponse.from_orm(track) for track in popular_tracks]