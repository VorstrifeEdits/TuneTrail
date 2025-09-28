from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.playlist import (
    Playlist,
    PlaylistTrack,
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
    PlaylistSummary,
    AddTracksToPlaylist,
    ReorderTracks,
    PlaylistTrackInfo,
)
from models.track import Track
from middleware.auth import get_current_user

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """
    Create a new playlist.

    Creates a playlist and optionally adds tracks to it in one operation.

    **Required scopes**: `write:playlists`
    """
    playlist = Playlist(
        name=playlist_data.name,
        description=playlist_data.description,
        is_public=playlist_data.is_public,
        cover_url=playlist_data.cover_url,
        user_id=current_user.id,
        org_id=current_user.org_id,
    )

    db.add(playlist)
    await db.flush()

    if playlist_data.track_ids:
        for position, track_id in enumerate(playlist_data.track_ids):
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
                    detail=f"Track {track_id} not found",
                )

            playlist_track = PlaylistTrack(
                playlist_id=playlist.id,
                track_id=track_id,
                position=position,
                added_by=current_user.id,
            )
            db.add(playlist_track)

    await db.commit()
    await db.refresh(playlist)

    return await _build_playlist_response(playlist, db)


@router.get("/", response_model=List[PlaylistSummary])
async def list_playlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of playlists to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of playlists to return"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
) -> List[PlaylistSummary]:
    """
    List all playlists for the current user.

    Returns playlists owned by the user. Optionally filter by public/private.

    **Required scopes**: `read:playlists`
    """
    query = select(Playlist).where(Playlist.user_id == current_user.id)

    if is_public is not None:
        query = query.where(Playlist.is_public == is_public)

    query = query.offset(skip).limit(limit).order_by(Playlist.updated_at.desc())

    result = await db.execute(query)
    playlists = result.scalars().all()

    summaries = []
    for playlist in playlists:
        track_count_query = select(func.count(PlaylistTrack.id)).where(
            PlaylistTrack.playlist_id == playlist.id
        )
        track_count = await db.scalar(track_count_query) or 0

        summaries.append(
            PlaylistSummary(
                id=playlist.id,
                name=playlist.name,
                description=playlist.description,
                is_public=playlist.is_public,
                track_count=track_count,
                cover_url=playlist.cover_url,
                created_at=playlist.created_at,
                updated_at=playlist.updated_at,
            )
        )

    return summaries


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """
    Get a specific playlist with all tracks.

    Returns detailed playlist information including all tracks in order.

    **Required scopes**: `read:playlists`
    """
    result = await db.execute(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(selectinload(Playlist.playlist_tracks))
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this playlist",
        )

    return await _build_playlist_response(playlist, db)


@router.patch("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: UUID,
    playlist_update: PlaylistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """
    Update playlist metadata.

    Allows updating name, description, cover image, and privacy settings.

    **Required scopes**: `write:playlists`
    """
    result = await db.execute(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    update_data = playlist_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(playlist, field, value)

    playlist.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(playlist)

    return await _build_playlist_response(playlist, db)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a playlist.

    Permanently removes the playlist and all track associations.

    **Required scopes**: `delete:playlists`
    """
    result = await db.execute(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    await db.delete(playlist)
    await db.commit()


@router.post("/{playlist_id}/tracks", response_model=PlaylistResponse)
async def add_tracks_to_playlist(
    playlist_id: UUID,
    tracks_data: AddTracksToPlaylist,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> PlaylistResponse:
    """
    Add tracks to a playlist.

    Adds one or more tracks to the end of the playlist.

    **Required scopes**: `write:playlists`
    """
    result = await db.execute(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    current_max_position_query = select(func.max(PlaylistTrack.position)).where(
        PlaylistTrack.playlist_id == playlist_id
    )
    current_max_position = await db.scalar(current_max_position_query) or -1

    for idx, track_id in enumerate(tracks_data.track_ids):
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
                detail=f"Track {track_id} not found",
            )

        existing_query = select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        )
        existing = await db.scalar(existing_query)

        if existing:
            continue

        playlist_track = PlaylistTrack(
            playlist_id=playlist_id,
            track_id=track_id,
            position=current_max_position + idx + 1,
            added_by=current_user.id,
        )
        db.add(playlist_track)

    playlist.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(playlist)

    return await _build_playlist_response(playlist, db)


@router.delete("/{playlist_id}/tracks/{track_id}", response_model=PlaylistResponse)
async def remove_track_from_playlist(
    playlist_id: UUID,
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """
    Remove a track from a playlist.

    Removes the specified track and reorders remaining tracks.

    **Required scopes**: `write:playlists`
    """
    result = await db.execute(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    await db.execute(
        delete(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        )
    )

    remaining_tracks = await db.execute(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position)
    )

    for new_position, playlist_track in enumerate(remaining_tracks.scalars().all()):
        playlist_track.position = new_position

    playlist.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(playlist)

    return await _build_playlist_response(playlist, db)


@router.post("/{playlist_id}/tracks/reorder", response_model=PlaylistResponse)
async def reorder_playlist_tracks(
    playlist_id: UUID,
    reorder_data: ReorderTracks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """
    Reorder tracks in a playlist.

    Move a track to a new position, shifting other tracks accordingly.

    **Required scopes**: `write:playlists`
    """
    result = await db.execute(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found",
        )

    tracks_result = await db.execute(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position)
    )
    all_tracks = list(tracks_result.scalars().all())

    target_track = next(
        (pt for pt in all_tracks if pt.track_id == reorder_data.track_id), None
    )

    if not target_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found in playlist",
        )

    all_tracks.remove(target_track)
    all_tracks.insert(reorder_data.new_position, target_track)

    for new_position, playlist_track in enumerate(all_tracks):
        playlist_track.position = new_position

    playlist.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(playlist)

    return await _build_playlist_response(playlist, db)


async def _build_playlist_response(playlist: Playlist, db: AsyncSession) -> PlaylistResponse:
    """Helper function to build a complete playlist response with tracks."""
    tracks_query = (
        select(PlaylistTrack, Track)
        .join(Track, PlaylistTrack.track_id == Track.id)
        .where(PlaylistTrack.playlist_id == playlist.id)
        .order_by(PlaylistTrack.position)
    )

    result = await db.execute(tracks_query)
    playlist_tracks_data = result.all()

    tracks_info = [
        PlaylistTrackInfo(
            id=track.id,
            title=track.title,
            artist=track.artist,
            duration_seconds=track.duration_seconds,
            position=pt.position,
            added_at=pt.added_at,
        )
        for pt, track in playlist_tracks_data
    ]

    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        is_public=playlist.is_public,
        cover_url=playlist.cover_url,
        user_id=playlist.user_id,
        track_count=len(tracks_info),
        tracks=tracks_info,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )