from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, EmailStr

from database import get_db
from models.user import User, UserResponse, UserUpdate
from models.track import Track, TrackResponse
from models.interaction import Interaction, InteractionType
from models.playlist import Playlist, PlaylistSummary
from middleware.auth import get_current_user

router = APIRouter(prefix="/users/me", tags=["User Profile"])


class UserPreferences(BaseModel):
    """Detailed user preferences for personalization."""
    favorite_genres: List[str] = Field(default_factory=list, example=["Rock", "Electronic", "Jazz"])
    disliked_genres: List[str] = Field(default_factory=list, example=["Country"])
    favorite_artists: List[str] = Field(default_factory=list, example=["Queen", "Daft Punk"])
    explicit_content_filter: bool = Field(default=False, description="Block explicit content")
    discovery_mode: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0 = safe/familiar, 1.0 = adventurous/discovery",
    )
    language_preferences: List[str] = Field(default_factory=list, example=["en", "es"])
    mood_preferences: dict = Field(
        default_factory=dict,
        example={"morning": "energetic", "evening": "calm", "night": "ambient"},
    )
    playback_settings: dict = Field(
        default_factory=dict,
        example={"crossfade_duration": 5, "normalize_volume": True, "gapless_playback": True},
    )


class UserSettings(BaseModel):
    """App settings and privacy controls."""
    theme: str = Field(default="dark", pattern="^(light|dark|auto)$")
    language: str = Field(default="en", min_length=2, max_length=5)
    notifications_enabled: bool = True
    email_notifications: bool = True
    public_profile: bool = Field(default=False, description="Make profile visible to others")
    show_listening_history: bool = Field(default=False, description="Make listening history public")
    allow_explicit_content: bool = True


class UserProfileUpdate(BaseModel):
    """User profile update payload."""
    full_name: Optional[str] = Field(None, max_length=255, example="John Doe")
    username: Optional[str] = Field(None, min_length=3, max_length=100, example="musiclover123")
    avatar_url: Optional[str] = Field(None, example="https://example.com/avatar.jpg")
    bio: Optional[str] = Field(None, max_length=500, example="Music enthusiast and playlist curator")
    location: Optional[str] = Field(None, max_length=100, example="San Francisco, CA")
    website: Optional[str] = Field(None, example="https://example.com")


class RecentlyPlayedItem(BaseModel):
    """A recently played track with play context."""
    track: TrackResponse
    played_at: datetime
    context: dict = Field(default_factory=dict, description="Playback context (playlist, etc.)")

    class Config:
        from_attributes = True


@router.get("/", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user's full profile.

    Returns comprehensive user information including stats.
    """
    return UserResponse.from_orm(current_user)


@router.put("/", response_model=UserResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user's profile.

    Allows updating display name, avatar, bio, and other profile fields.
    """
    update_dict = profile_data.model_dump(exclude_unset=True)

    if "username" in update_dict and update_dict["username"]:
        existing_user_query = select(User).where(
            User.username == update_dict["username"],
            User.id != current_user.id,
        )
        existing = await db.scalar(existing_user_query)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    for field, value in update_dict.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_orm(current_user)


@router.get("/preferences", response_model=UserPreferences)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
) -> UserPreferences:
    """
    Get user's preferences for personalization.

    Returns detailed preferences used by recommendation engine.
    """
    prefs = current_user.preferences or {}
    return UserPreferences(**prefs)


@router.put("/preferences", response_model=UserPreferences)
async def update_my_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferences:
    """
    Update user preferences.

    Used for personalizing recommendations and user experience.
    Changes take effect immediately in recommendation engine.
    """
    current_user.preferences = preferences.model_dump()
    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return preferences


@router.get("/recently-played", response_model=List[RecentlyPlayedItem])
async def get_recently_played(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Number of recent tracks"),
    days: int = Query(30, ge=1, le=365, description="Look back period in days"),
) -> List[RecentlyPlayedItem]:
    """
    Get recently played tracks.

    Returns user's listening history in reverse chronological order.

    **Use Cases:**
    - "Continue where you left off"
    - Listening history
    - Recently played section in UI

    **Required scopes**: `read:interactions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Interaction, Track)
        .join(Track, Interaction.track_id == Track.id)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == InteractionType.PLAY.value,
            Interaction.created_at >= cutoff_date,
        )
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    recently_played = [
        RecentlyPlayedItem(
            track=TrackResponse.from_orm(track),
            played_at=interaction.created_at,
            context=interaction.context or {},
        )
        for interaction, track in rows
    ]

    return recently_played


@router.get("/favorites", response_model=List[TrackResponse])
async def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500, description="Number of favorite tracks"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
) -> List[TrackResponse]:
    """
    Get user's favorite (liked) tracks.

    Returns all tracks the user has liked, ordered by most recent.

    **Quick Access to:**
    - All liked tracks
    - Favorite songs collection
    - Easy playlist creation from favorites

    **Required scopes**: `read:interactions`
    """
    query = (
        select(Track)
        .join(Interaction, Interaction.track_id == Track.id)
        .where(
            Interaction.user_id == current_user.id,
            Interaction.interaction_type == InteractionType.LIKE.value,
        )
        .order_by(Interaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    favorite_tracks = result.scalars().all()

    return [TrackResponse.from_orm(track) for track in favorite_tracks]


@router.get("/library/artists")
async def get_my_artists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
) -> List[dict]:
    """
    Get all artists in user's library.

    Returns unique artists with track counts, ordered by track count.

    **Use Cases:**
    - Browse library by artist
    - Artist collection overview
    - Quick artist navigation

    **Required scopes**: `read:tracks`
    """
    query = (
        select(
            Track.artist,
            func.count(Track.id).label("track_count"),
            func.array_agg(func.distinct(Track.genre)).label("genres"),
        )
        .where(
            Track.org_id == current_user.org_id,
            Track.artist.isnot(None),
        )
        .group_by(Track.artist)
        .order_by(func.count(Track.id).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    artists = [
        {
            "name": row[0],
            "track_count": row[1],
            "genres": [g for g in row[2] if g] if row[2] else [],
        }
        for row in result.all()
    ]

    return artists


@router.get("/library/genres")
async def get_my_genres(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """
    Get all genres in user's library with track counts.

    **Use Cases:**
    - Browse by genre
    - Genre statistics
    - Library organization

    **Required scopes**: `read:tracks`
    """
    query = (
        select(Track.genre, func.count(Track.id).label("track_count"))
        .where(
            Track.org_id == current_user.org_id,
            Track.genre.isnot(None),
        )
        .group_by(Track.genre)
        .order_by(func.count(Track.id).desc())
    )

    result = await db.execute(query)
    genres = [{"name": row[0], "track_count": row[1]} for row in result.all()]

    return genres


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete current user account.

    **GDPR Compliance - Right to be Forgotten**

    This permanently deletes:
    - User profile
    - All interactions
    - All playlists
    - All API keys
    - All data associated with the account

    **This action cannot be undone!**
    """
    await db.delete(current_user)
    await db.commit()