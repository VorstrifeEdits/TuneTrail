from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models.user import User, UserResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class OnboardingPreferences(BaseModel):
    """
    Initial music preferences for cold-start recommendations.

    **Critical for ML:** Bootstrap recommendation engine before user has listening history.
    """
    favorite_genres: List[str] = Field(
        ...,
        min_items=3,
        max_items=10,
        example=["Rock", "Electronic", "Jazz", "Hip Hop", "Classical"],
        description="User's favorite music genres (3-10 required for good recommendations)",
    )
    disliked_genres: List[str] = Field(
        default_factory=list,
        max_items=5,
        example=["Country", "Opera"],
        description="Genres to avoid in recommendations",
    )
    favorite_artists: List[str] = Field(
        default_factory=list,
        min_items=0,
        max_items=20,
        example=["Queen", "Daft Punk", "Miles Davis", "Kendrick Lamar"],
        description="Favorite artists (helps seed recommendations)",
    )
    favorite_decades: List[str] = Field(
        default_factory=list,
        example=["1980s", "1990s", "2000s"],
        description="Preferred music eras",
    )

    discovery_mode: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0.0 = only play safe/familiar, 1.0 = maximum exploration/discovery",
    )

    energy_preference: str = Field(
        default="medium",
        pattern="^(low|medium|high|mixed)$",
        description="Preferred energy level",
    )

    listening_contexts: List[str] = Field(
        default_factory=list,
        example=["workout", "study", "commute", "party"],
        description="Primary listening activities",
    )


class OnboardingStatus(BaseModel):
    """Track onboarding progress."""
    current_step: str = Field(..., example="preferences")
    completed_steps: List[str] = []
    total_steps: int = 3
    progress_percentage: float


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
) -> OnboardingStatus:
    """
    Get user's onboarding progress.

    **Steps:**
    1. Account creation (email, password, name)
    2. Music preferences (genres, artists)
    3. Profile completion (optional: avatar, bio)

    **Frontend Use:**
    - Show onboarding wizard
    - Skip if completed
    - Resume where user left off
    """
    completed_steps = []

    if current_user.email_verified:
        completed_steps.append("account_created")

    prefs = current_user.preferences or {}
    if prefs.get("favorite_genres"):
        completed_steps.append("preferences")

    if current_user.avatar_url or current_user.bio:
        completed_steps.append("profile")

    current_step = current_user.onboarding_step or "account_created"
    if current_user.profile_completed_at:
        current_step = "completed"

    return OnboardingStatus(
        current_step=current_step,
        completed_steps=completed_steps,
        total_steps=3,
        progress_percentage=round(len(completed_steps) / 3 * 100, 2),
    )


@router.post("/preferences", response_model=UserResponse)
async def set_onboarding_preferences(
    preferences: OnboardingPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Set initial music preferences during onboarding.

    **ML CRITICAL:** Cold-start solution for new users.

    **Without This:**
    - New users get random recommendations
    - Poor initial experience
    - High churn rate

    **With This:**
    - Immediate personalized recommendations
    - Better first impression
    - Higher engagement

    **Data Used By:**
    - Content-based filtering (genre matching)
    - Collaborative filtering (find similar users)
    - Hybrid models (weighted combination)
    """
    current_user.preferences = current_user.preferences or {}

    current_user.preferences.update({
        "favorite_genres": preferences.favorite_genres,
        "disliked_genres": preferences.disliked_genres,
        "favorite_artists": preferences.favorite_artists,
        "favorite_decades": preferences.favorite_decades,
        "discovery_mode": preferences.discovery_mode,
        "energy_preference": preferences.energy_preference,
        "listening_contexts": preferences.listening_contexts,
        "onboarding_completed_at": datetime.utcnow().isoformat(),
    })

    current_user.onboarding_step = "profile"
    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_orm(current_user)


@router.post("/complete", response_model=UserResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Mark onboarding as complete.

    **Triggers:**
    - Initial recommendation generation
    - Welcome email
    - Tip notifications

    **Frontend:**
    - Redirect to main app
    - Show "Get Started" tutorial
    """
    prefs = current_user.preferences or {}

    if not prefs.get("favorite_genres"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete music preferences first",
        )

    current_user.profile_completed_at = datetime.utcnow()
    current_user.onboarding_step = "completed"
    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_orm(current_user)


@router.post("/skip", response_model=UserResponse)
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Skip onboarding (not recommended).

    User can complete later from settings.
    Recommendations will be generic until preferences are set.
    """
    current_user.onboarding_step = "skipped"
    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.from_orm(current_user)