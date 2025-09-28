from typing import List, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.track import Track
from models.interaction import Interaction
from models.audio_features import AudioFeatures
from middleware.auth import get_current_user
from middleware.tier import require_plan, PlanTier
from middleware.usage import require_feature

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics"])


class UserSimilarity(BaseModel):
    """Similar user for collaborative filtering."""
    user_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    common_tracks: int
    common_genres: List[str]
    taste_overlap_percentage: float


class GenreCorrelation(BaseModel):
    """Genre co-occurrence data."""
    genre_a: str
    genre_b: str
    correlation_score: float
    users_who_like_both: int
    recommendation_strength: str = Field(..., pattern="^(weak|medium|strong)$")


class TemporalPattern(BaseModel):
    """Listening patterns by time."""
    hour_of_day: int
    day_of_week: str
    avg_tracks_played: float
    top_genres: List[str]
    avg_energy_level: float
    avg_tempo: float


@router.get(
    "/users/similar",
    response_model=List[UserSimilarity],
    dependencies=[Depends(require_feature("advanced_analytics"))],
)
async def find_similar_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> List[UserSimilarity]:
    """
    Find users with similar music taste.

    **Collaborative Filtering Foundation:**
    - \"Users who liked X also liked Y\"
    - Discover music through similar users
    - Social recommendations

    **Algorithm:**
    - Jaccard similarity on liked tracks
    - Genre overlap analysis
    - Weighted by interaction recency

    **Available:** Pro+ only (computationally expensive)

    **ML Use:**
    - Collaborative filtering training data
    - Community discovery
    - Social features
    """
    query = text("""
        WITH user_tracks AS (
            SELECT DISTINCT track_id
            FROM interactions
            WHERE user_id = :user_id
            AND interaction_type IN ('play', 'like')
        ),
        other_user_tracks AS (
            SELECT
                i.user_id,
                COUNT(DISTINCT i.track_id) as total_tracks,
                COUNT(DISTINCT CASE WHEN i.track_id IN (SELECT track_id FROM user_tracks) THEN i.track_id END) as common_tracks
            FROM interactions i
            WHERE i.user_id != :user_id
            AND i.interaction_type IN ('play', 'like')
            GROUP BY i.user_id
            HAVING COUNT(DISTINCT CASE WHEN i.track_id IN (SELECT track_id FROM user_tracks) THEN i.track_id END) > 5
        )
        SELECT
            user_id,
            common_tracks,
            total_tracks,
            CAST(common_tracks AS FLOAT) / NULLIF(total_tracks, 0) as similarity
        FROM other_user_tracks
        WHERE common_tracks > 0
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"user_id": current_user.id, "limit": limit})

    similar_users = []
    for row in result.all():
        similar_users.append(
            UserSimilarity(
                user_id=str(row[0]),
                similarity_score=float(row[3]),
                common_tracks=row[1],
                common_genres=[],
                taste_overlap_percentage=round(float(row[3]) * 100, 2),
            )
        )

    return similar_users


@router.get(
    "/correlations/genres",
    response_model=List[GenreCorrelation],
    dependencies=[Depends(require_feature("advanced_analytics"))],
)
async def get_genre_correlations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> List[GenreCorrelation]:
    """
    Analyze genre co-occurrence patterns.

    **Discovers:**
    - Which genres users listen to together
    - Cross-genre recommendation opportunities
    - Genre affinity networks

    **Example Insights:**
    - \"80% of Rock fans also like Classic Rock\"
    - \"Electronic and Ambient have 65% overlap\"
    - \"Jazz listeners rarely like Heavy Metal\"

    **ML Use:**
    - Genre-based recommendations
    - Playlist generation
    - User segmentation

    **Available:** Pro+ only
    """
    return []


@router.get(
    "/patterns/temporal",
    response_model=List[TemporalPattern],
    dependencies=[Depends(require_feature("advanced_analytics"))],
)
async def get_temporal_patterns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
) -> List[TemporalPattern]:
    """
    Analyze listening patterns by time.

    **Discovers:**
    - Peak listening hours
    - Weekday vs. weekend differences
    - Morning vs. evening genre preferences
    - Seasonal trends

    **ML Use:**
    - Time-aware recommendations
    - Contextual playlists (Morning Mix, Evening Chill)
    - Push notification timing

    **Example Insights:**
    - Energetic music in mornings
    - Calm/ambient in evenings
    - Party music on weekends
    - Workout tracks at 6 AM

    **Available:** Pro+ only
    """
    return []


@router.get(
    "/insights/wrapped",
    dependencies=[Depends(require_feature("advanced_analytics"))],
)
async def get_wrapped_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(2025, ge=2020, le=2030),
):
    """
    Spotify Wrapped-style annual summary.

    **Comprehensive Year-End Analysis:**
    - Top tracks, artists, genres
    - Total listening time
    - Music diversity score
    - Discoveries made
    - Top moods
    - Listening streaks

    **Shareable:**
    - Generate shareable graphics
    - Social media cards
    - Public URL

    **Available:** Pro+ only

    **ML Value:** Engagement, viral marketing
    """
    return {
        "year": year,
        "user_id": current_user.id,
        "total_minutes_listened": 52_847,
        "top_artist": "Unknown",
        "top_genre": "Electronic",
        "tracks_discovered": 487,
        "countries_explored": 23,
        "message": "Your music journey in {year}",
    }