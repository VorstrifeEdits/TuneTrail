from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.user import User
from models.track import Track, TrackCreate, TrackResponse, TrackUpdate
from middleware.auth import get_current_user

router = APIRouter(prefix="/tracks", tags=["Tracks"])


@router.post("/", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def create_track(
    track_data: TrackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackResponse:
    """
    Create a new music track.

    Adds a track to your library with metadata. The track will be associated
    with your organization.

    **Required scopes**: `write:tracks`
    """
    track = Track(
        **track_data.model_dump(),
        org_id=current_user.org_id,
    )

    db.add(track)
    await db.commit()
    await db.refresh(track)

    return TrackResponse.from_orm(track)


@router.get("/", response_model=List[TrackResponse])
async def list_tracks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of tracks to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tracks to return"),
    artist: Optional[str] = Query(None, description="Filter by artist name"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
) -> List[TrackResponse]:
    """
    List all tracks in your library.

    Supports pagination and filtering by artist or genre.

    **Required scopes**: `read:tracks`
    """
    query = select(Track).where(Track.org_id == current_user.org_id)

    if artist:
        query = query.where(Track.artist.ilike(f"%{artist}%"))
    if genre:
        query = query.where(Track.genre == genre)

    query = query.offset(skip).limit(limit).order_by(Track.created_at.desc())

    result = await db.execute(query)
    tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in tracks]


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackResponse:
    """
    Get a specific track by ID.

    Returns detailed information about a single track.

    **Required scopes**: `read:tracks`
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

    return TrackResponse.from_orm(track)


@router.patch("/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: UUID,
    track_update: TrackUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackResponse:
    """
    Update a track's metadata.

    Allows updating track information like title, artist, genre, etc.

    **Required scopes**: `write:tracks`
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

    # Update fields
    update_data = track_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(track, field, value)

    await db.commit()
    await db.refresh(track)

    return TrackResponse.from_orm(track)


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a track from your library.

    Permanently removes the track and all associated data.

    **Required scopes**: `delete:tracks`
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

    await db.delete(track)
    await db.commit()


@router.get("/stats/summary")
async def get_track_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about your track library.

    Returns summary statistics including total tracks, genres, artists, etc.
    """
    total_tracks_query = select(func.count(Track.id)).where(
        Track.org_id == current_user.org_id
    )
    total_tracks = await db.scalar(total_tracks_query)

    unique_artists_query = select(func.count(func.distinct(Track.artist))).where(
        Track.org_id == current_user.org_id
    )
    unique_artists = await db.scalar(unique_artists_query)

    unique_genres_query = select(func.count(func.distinct(Track.genre))).where(
        Track.org_id == current_user.org_id
    )
    unique_genres = await db.scalar(unique_genres_query)

    return {
        "total_tracks": total_tracks or 0,
        "unique_artists": unique_artists or 0,
        "unique_genres": unique_genres or 0,
    }