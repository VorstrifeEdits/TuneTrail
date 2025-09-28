from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.interaction import (
    Interaction,
    InteractionCreate,
    InteractionResponse,
    InteractionStats,
    InteractionType,
)
from models.track import Track
from middleware.auth import get_current_user

router = APIRouter(prefix="/interactions", tags=["Interactions"])


@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def record_interaction(
    interaction_data: InteractionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> InteractionResponse:
    """
    Record a user interaction with a track.

    Tracks user behavior for collaborative filtering and analytics.
    Supported interaction types: play, skip, like, dislike, playlist_add, share.

    **Required scopes**: `write:interactions`
    """
    result = await db.execute(
        select(Track).where(
            Track.id == interaction_data.track_id,
            Track.org_id == current_user.org_id,
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    interaction = Interaction(
        user_id=current_user.id,
        track_id=interaction_data.track_id,
        interaction_type=interaction_data.interaction_type.value,
        rating=interaction_data.rating,
        play_duration_seconds=interaction_data.play_duration_seconds,
        context=interaction_data.context,
    )

    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    return InteractionResponse.from_orm(interaction)


@router.get("/", response_model=List[InteractionResponse])
async def list_interactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of interactions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of interactions to return"),
    interaction_type: Optional[InteractionType] = Query(None, description="Filter by interaction type"),
    track_id: Optional[UUID] = Query(None, description="Filter by specific track"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> List[InteractionResponse]:
    """
    List user's interaction history.

    Returns chronological list of all interactions, optionally filtered.

    **Required scopes**: `read:interactions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = select(Interaction).where(
        Interaction.user_id == current_user.id,
        Interaction.created_at >= cutoff_date,
    )

    if interaction_type:
        query = query.where(Interaction.interaction_type == interaction_type.value)

    if track_id:
        query = query.where(Interaction.track_id == track_id)

    query = query.offset(skip).limit(limit).order_by(Interaction.created_at.desc())

    result = await db.execute(query)
    interactions = result.scalars().all()

    return [InteractionResponse.from_orm(i) for i in interactions]


@router.get("/stats", response_model=InteractionStats)
async def get_interaction_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> InteractionStats:
    """
    Get aggregate interaction statistics for the current user.

    Returns insights about listening behavior, favorite genres, top artists, etc.

    **Required scopes**: `read:interactions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    total_plays_query = select(func.count(Interaction.id)).where(
        Interaction.user_id == current_user.id,
        Interaction.interaction_type == "play",
        Interaction.created_at >= cutoff_date,
    )
    total_plays = await db.scalar(total_plays_query) or 0

    total_likes_query = select(func.count(Interaction.id)).where(
        Interaction.user_id == current_user.id,
        Interaction.interaction_type == "like",
        Interaction.created_at >= cutoff_date,
    )
    total_likes = await db.scalar(total_likes_query) or 0

    total_skips_query = select(func.count(Interaction.id)).where(
        Interaction.user_id == current_user.id,
        Interaction.interaction_type == "skip",
        Interaction.created_at >= cutoff_date,
    )
    total_skips = await db.scalar(total_skips_query) or 0

    unique_tracks_query = select(func.count(func.distinct(Interaction.track_id))).where(
        Interaction.user_id == current_user.id,
        Interaction.interaction_type == "play",
        Interaction.created_at >= cutoff_date,
    )
    unique_tracks_played = await db.scalar(unique_tracks_query) or 0

    total_play_time_query = select(func.sum(Interaction.play_duration_seconds)).where(
        Interaction.user_id == current_user.id,
        Interaction.interaction_type == "play",
        Interaction.created_at >= cutoff_date,
    )
    total_play_time_seconds = await db.scalar(total_play_time_query) or 0
    total_play_time_hours = round(total_play_time_seconds / 3600, 2)

    top_genres_query = (
        select(Track.genre, func.count(Interaction.id).label("play_count"))
        .join(Interaction, Interaction.track_id == Track.id)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == "play",
            Interaction.created_at >= cutoff_date,
            Track.genre.isnot(None),
        )
        .group_by(Track.genre)
        .order_by(func.count(Interaction.id).desc())
        .limit(5)
    )
    genres_result = await db.execute(top_genres_query)
    favorite_genres = [row[0] for row in genres_result.all()]

    top_artists_query = (
        select(Track.artist, func.count(Interaction.id).label("play_count"))
        .join(Interaction, Interaction.track_id == Track.id)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == "play",
            Interaction.created_at >= cutoff_date,
            Track.artist.isnot(None),
        )
        .group_by(Track.artist)
        .order_by(func.count(Interaction.id).desc())
        .limit(5)
    )
    artists_result = await db.execute(top_artists_query)
    top_artists = [row[0] for row in artists_result.all()]

    return InteractionStats(
        total_plays=total_plays,
        total_likes=total_likes,
        total_skips=total_skips,
        unique_tracks_played=unique_tracks_played,
        total_play_time_hours=total_play_time_hours,
        favorite_genres=favorite_genres,
        top_artists=top_artists,
    )