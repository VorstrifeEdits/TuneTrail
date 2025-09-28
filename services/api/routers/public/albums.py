from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists, delete
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.album import Album, SavedAlbum, AlbumResponse
from models.track import Track, TrackResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/albums", tags=["Albums"])


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlbumResponse:
    """
    Get album details.

    Returns album metadata without tracks. Use `/albums/{id}/tracks` for tracks.
    """
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.org_id == current_user.org_id,
        )
    )
    album = result.scalar_one_or_none()

    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        )

    return AlbumResponse.from_orm(album)


@router.get("/{album_id}/tracks", response_model=List[TrackResponse])
async def get_album_tracks(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TrackResponse]:
    """
    Get all tracks in an album.

    Returns tracks in album order.
    """
    result = await db.execute(
        select(Track).where(
            Track.album == album_id,
            Track.org_id == current_user.org_id,
        )
    )
    tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in tracks]


@router.get("/", response_model=List[AlbumResponse])
async def list_albums(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    artist: Optional[str] = Query(None, description="Filter by artist"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
) -> List[AlbumResponse]:
    """
    List all albums.

    Optionally filter by artist.
    """
    query = select(Album).where(Album.org_id == current_user.org_id)

    if artist:
        query = query.where(Album.artist.ilike(f"%{artist}%"))

    query = query.order_by(Album.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    albums = result.scalars().all()

    return [AlbumResponse.from_orm(album) for album in albums]


@router.post("/me/saved", status_code=status.HTTP_204_NO_CONTENT)
async def save_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Save album to user's library.

    Similar to Spotify's "Save Album" feature.
    """
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.org_id == current_user.org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        )

    existing_query = select(SavedAlbum).where(
        SavedAlbum.user_id == current_user.id,
        SavedAlbum.album_id == album_id,
    )
    if await db.scalar(existing_query):
        return

    saved = SavedAlbum(user_id=current_user.id, album_id=album_id)
    db.add(saved)
    await db.commit()


@router.delete("/me/saved/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Remove album from user's library.
    """
    await db.execute(
        delete(SavedAlbum).where(
            SavedAlbum.user_id == current_user.id,
            SavedAlbum.album_id == album_id,
        )
    )
    await db.commit()


@router.get("/me/saved", response_model=List[AlbumResponse])
async def get_saved_albums(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    skip: int = 0,
) -> List[AlbumResponse]:
    """
    Get user's saved albums.

    Returns albums in order of when they were saved.
    """
    query = (
        select(Album)
        .join(SavedAlbum, SavedAlbum.album_id == Album.id)
        .where(SavedAlbum.user_id == current_user.id)
        .order_by(SavedAlbum.saved_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    albums = result.scalars().all()

    return [AlbumResponse.from_orm(album) for album in albums]