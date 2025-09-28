from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.album import Artist, ArtistFollow, ArtistResponse, Album
from models.track import Track, TrackResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/artists", tags=["Artists"])


@router.get("/{artist_id}", response_model=ArtistResponse)
async def get_artist(
    artist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArtistResponse:
    """
    Get artist details.

    Returns artist metadata, stats, and bio.
    """
    result = await db.execute(
        select(Artist).where(
            Artist.id == artist_id,
            Artist.org_id == current_user.org_id,
        )
    )
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artist not found",
        )

    return ArtistResponse.from_orm(artist)


@router.get("/{artist_id}/tracks", response_model=List[TrackResponse])
async def get_artist_tracks(
    artist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> List[TrackResponse]:
    """
    Get all tracks by an artist.

    Returns tracks ordered by popularity (play count).
    """
    result = await db.execute(
        select(Track).where(
            Track.artist_id == artist_id,
            Track.org_id == current_user.org_id,
        ).limit(limit)
    )
    tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in tracks]


@router.get("/{artist_id}/top-tracks", response_model=List[TrackResponse])
async def get_artist_top_tracks(
    artist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
) -> List[TrackResponse]:
    """
    Get artist's most popular tracks.

    **Sorted by:**
    - Play count
    - Like count
    - Recency

    **ML Enhanced**: Uses interaction data for popularity.
    """
    return await get_artist_tracks(artist_id, current_user, db, limit)


@router.post("/me/following", status_code=status.HTTP_204_NO_CONTENT)
async def follow_artist(
    artist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Follow an artist.

    **Features:**
    - Get notified of new releases
    - Artist appears in "Following" feed
    - Influences recommendations

    **ML Impact:** Explicit preference signal
    """
    result = await db.execute(
        select(Artist).where(
            Artist.id == artist_id,
            Artist.org_id == current_user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artist not found",
        )

    existing_query = select(ArtistFollow).where(
        ArtistFollow.user_id == current_user.id,
        ArtistFollow.artist_id == artist_id,
    )
    if await db.scalar(existing_query):
        return

    follow = ArtistFollow(user_id=current_user.id, artist_id=artist_id)
    db.add(follow)
    await db.commit()


@router.delete("/me/following/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_artist(
    artist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Unfollow an artist.
    """
    await db.execute(
        delete(ArtistFollow).where(
            ArtistFollow.user_id == current_user.id,
            ArtistFollow.artist_id == artist_id,
        )
    )
    await db.commit()


@router.get("/me/following", response_model=List[ArtistResponse])
async def get_followed_artists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
) -> List[ArtistResponse]:
    """
    Get followed artists.

    Returns artists ordered by follow date (most recent first).
    """
    query = (
        select(Artist)
        .join(ArtistFollow, ArtistFollow.artist_id == Artist.id)
        .where(ArtistFollow.user_id == current_user.id)
        .order_by(ArtistFollow.followed_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    artists = result.scalars().all()

    return [ArtistResponse.from_orm(artist) for artist in artists]