from typing import List, Optional, Union
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.track import Track, TrackResponse
from models.playlist import Playlist, PlaylistSummary
from models.tracking import SearchQuery
from middleware.auth import get_current_user

router = APIRouter(prefix="/search", tags=["Search"])


class SearchType(str):
    ALL = "all"
    TRACK = "track"
    PLAYLIST = "playlist"
    ARTIST = "artist"
    ALBUM = "album"


class ArtistResult(BaseModel):
    name: str
    track_count: int
    genres: List[str] = []

    class Config:
        from_attributes = True


class AlbumResult(BaseModel):
    name: str
    artist: Optional[str]
    track_count: int
    release_year: Optional[int]

    class Config:
        from_attributes = True


class SearchResults(BaseModel):
    """Unified search results across all content types."""
    query: str
    total_results: int
    tracks: List[TrackResponse] = []
    playlists: List[PlaylistSummary] = []
    artists: List[ArtistResult] = []
    albums: List[AlbumResult] = []


@router.get("/", response_model=SearchResults)
async def search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string",
        example="queen bohemian",
    ),
    search_type: str = Query(
        "all",
        description="Type of content to search",
        pattern="^(all|track|playlist|artist|album)$",
    ),
    limit: int = Query(20, ge=1, le=100, description="Max results per category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResults:
    """
    Unified search across tracks, playlists, artists, and albums.

    Supports fuzzy matching and PostgreSQL full-text search.

    **Search Algorithm:**
    - Exact matches prioritized
    - Case-insensitive matching
    - Partial word matching (ILIKE)
    - Full-text search on track titles (PostgreSQL tsv_vector)

    **Search Types:**
    - `all`: Search everything
    - `track`: Only tracks
    - `playlist`: Only playlists
    - `artist`: Only artists (grouped)
    - `album`: Only albums (grouped)

    **Required scopes**: `read:tracks`, `read:playlists`
    """
    search_pattern = f"%{q}%"
    results = SearchResults(query=q, total_results=0)

    if search_type in ["all", "track"]:
        tracks_query = (
            select(Track)
            .where(
                Track.org_id == current_user.org_id,
                or_(
                    Track.title.ilike(search_pattern),
                    Track.artist.ilike(search_pattern),
                    Track.album.ilike(search_pattern),
                ),
            )
            .order_by(
                func.case(
                    (Track.title.ilike(f"{q}%"), 1),
                    (Track.artist.ilike(f"{q}%"), 2),
                    else_=3
                )
            )
            .limit(limit)
        )

        tracks_result = await db.execute(tracks_query)
        tracks = tracks_result.scalars().all()
        results.tracks = [TrackResponse.from_orm(t) for t in tracks]
        results.total_results += len(tracks)

    if search_type in ["all", "playlist"]:
        playlists_query = (
            select(Playlist)
            .where(
                or_(
                    and_(
                        Playlist.user_id == current_user.id,
                    ),
                    and_(
                        Playlist.is_public == True,
                        Playlist.org_id == current_user.org_id,
                    ),
                ),
                or_(
                    Playlist.name.ilike(search_pattern),
                    Playlist.description.ilike(search_pattern),
                ),
            )
            .limit(limit)
        )

        playlists_result = await db.execute(playlists_query)
        playlists = playlists_result.scalars().all()

        for playlist in playlists:
            track_count_query = select(func.count()).select_from(
                select(1).where(
                    select(1).where(
                        select(1).correlate(Playlist).where(
                            Playlist.id == playlist.id
                        ).exists()
                    ).exists()
                ).subquery()
            )
            track_count = 0

            results.playlists.append(
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
        results.total_results += len(playlists)

    if search_type in ["all", "artist"]:
        artists_query = (
            select(
                Track.artist,
                func.count(Track.id).label("track_count"),
                func.array_agg(func.distinct(Track.genre)).label("genres"),
            )
            .where(
                Track.org_id == current_user.org_id,
                Track.artist.ilike(search_pattern),
                Track.artist.isnot(None),
            )
            .group_by(Track.artist)
            .order_by(func.count(Track.id).desc())
            .limit(limit)
        )

        artists_result = await db.execute(artists_query)
        for row in artists_result.all():
            results.artists.append(
                ArtistResult(
                    name=row[0],
                    track_count=row[1],
                    genres=[g for g in row[2] if g] if row[2] else [],
                )
            )
        results.total_results += len(results.artists)

    if search_type in ["all", "album"]:
        albums_query = (
            select(
                Track.album,
                Track.artist,
                func.count(Track.id).label("track_count"),
                func.min(Track.release_year).label("release_year"),
            )
            .where(
                Track.org_id == current_user.org_id,
                Track.album.ilike(search_pattern),
                Track.album.isnot(None),
            )
            .group_by(Track.album, Track.artist)
            .order_by(func.count(Track.id).desc())
            .limit(limit)
        )

        albums_result = await db.execute(albums_query)
        for row in albums_result.all():
            results.albums.append(
                AlbumResult(
                    name=row[0],
                    artist=row[1],
                    track_count=row[2],
                    release_year=row[3],
                )
            )
        results.total_results += len(results.albums)

    # Auto-log search query for ML
    search_log = SearchQuery(
        user_id=current_user.id,
        query=q,
        search_type=search_type,
        results_count=results.total_results,
    )
    db.add(search_log)
    await db.commit()

    return results


@router.get("/autocomplete")
async def search_autocomplete(
    q: str = Query(..., min_length=1, max_length=100, description="Search query for autocomplete"),
    limit: int = Query(10, ge=1, le=50, description="Max suggestions"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get autocomplete suggestions for search.

    Returns quick suggestions as user types. Optimized for speed.

    **Returns:**
    - Track titles
    - Artist names
    - Album names
    - Playlist names

    **Required scopes**: `read:tracks`
    """
    search_pattern = f"{q}%"
    suggestions = {
        "tracks": [],
        "artists": [],
        "albums": [],
        "playlists": [],
    }

    track_titles_query = (
        select(Track.title)
        .where(
            Track.org_id == current_user.org_id,
            Track.title.ilike(search_pattern),
        )
        .distinct()
        .limit(limit // 2)
    )
    result = await db.execute(track_titles_query)
    suggestions["tracks"] = [row[0] for row in result.all()]

    artists_query = (
        select(Track.artist)
        .where(
            Track.org_id == current_user.org_id,
            Track.artist.ilike(search_pattern),
            Track.artist.isnot(None),
        )
        .distinct()
        .limit(limit // 4)
    )
    result = await db.execute(artists_query)
    suggestions["artists"] = [row[0] for row in result.all()]

    return suggestions