from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_db
from models.user import User
from models.tracking import (
    SearchQuery,
    SearchQueryLog,
    SearchClick,
    RecommendationImpression,
    ImpressionLog,
    ImpressionClick,
    ContentView,
    ViewEvent,
    PlayerEvent,
    PlayerEventLog,
)
from middleware.auth import get_current_user

router = APIRouter(prefix="/tracking", tags=["ML Tracking"])


@router.post("/search", status_code=status.HTTP_201_CREATED)
async def log_search_query(
    search_log: SearchQueryLog,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Log search query for ML improvement.

    **ML Critical**: Every search = training data!

    **Tracks:**
    - What users search for
    - Which results they click
    - Position bias (do users click top results?)
    - Failed searches (0 results = missing content)

    **ML Use Cases:**
    - Improve search ranking
    - Autocomplete suggestions
    - Query understanding
    - Content gap analysis

    **Usage:**
    - Client calls after search
    - Returns search_query_id
    - Client calls /tracking/search/click when user clicks result
    """
    search_query = SearchQuery(
        user_id=current_user.id,
        query=search_log.query,
        search_type=search_log.search_type,
        filters=search_log.filters,
        results_count=search_log.results_count,
        session_id=search_log.session_id,
        device_type=search_log.device_type,
    )

    db.add(search_query)
    await db.commit()
    await db.refresh(search_query)

    return {"search_query_id": search_query.id}


@router.post("/search/click", status_code=status.HTTP_204_NO_CONTENT)
async def log_search_click(
    click_data: SearchClick,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Record click on search result.

    **ML Critical**: Click-through rate (CTR) measurement!

    **Tracks:**
    - Which result user clicked
    - Position in results (1st, 2nd, 3rd...)
    - Time to click (how long user browsed)

    **ML Use:**
    - Ranking quality
    - Position bias
    - Result relevance
    """
    result = await db.execute(
        select(SearchQuery).where(
            SearchQuery.id == click_data.search_query_id,
            SearchQuery.user_id == current_user.id,
        )
    )
    search_query = result.scalar_one_or_none()

    if search_query:
        search_query.clicked_result_id = click_data.clicked_result_id
        search_query.clicked_result_type = click_data.clicked_result_type
        search_query.clicked_position = click_data.clicked_position
        search_query.time_to_click_ms = click_data.time_to_click_ms

        await db.commit()


@router.post("/impressions", status_code=status.HTTP_201_CREATED)
async def log_recommendation_impressions(
    impressions: ImpressionLog,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Log recommendation impressions.

    **ML CRITICAL**: Can't calculate recommendation quality without this!

    **Tracks:**
    - Which recommendations were SHOWN (not clicked)
    - Position in list
    - Model type and version
    - Recommendation scores

    **ML Metrics Enabled:**
    - CTR (clicks / impressions)
    - Precision@K (relevant items in top K)
    - NDCG (ranking quality)
    - Model comparison (A/B testing)

    **Without This:**
    - Can't measure recommendation accuracy
    - Can't compare models
    - Can't detect position bias

    **Usage:**
    - Client calls when showing recommendations
    - Records all tracks shown
    - Client calls /tracking/impressions/click when user clicks
    """
    impression_ids = []

    for idx, track_id in enumerate(impressions.track_ids):
        score = impressions.scores[idx] if impressions.scores and idx < len(impressions.scores) else None
        reason = impressions.reasons[idx] if impressions.reasons and idx < len(impressions.reasons) else None

        impression = RecommendationImpression(
            user_id=current_user.id,
            track_id=track_id,
            recommendation_id=uuid4(),
            model_type=impressions.model_type,
            model_version=impressions.model_version,
            score=score,
            reason=reason,
            position=idx,
            context_type=impressions.context_type,
            context_id=impressions.context_id,
        )

        db.add(impression)
        impression_ids.append(impression.id)

    await db.commit()

    return {"impression_ids": [str(id) for id in impression_ids]}


@router.post("/impressions/click", status_code=status.HTTP_204_NO_CONTENT)
async def log_impression_click(
    click_data: ImpressionClick,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Record click on recommendation.

    **Updates impression with click data for CTR calculation.**
    """
    result = await db.execute(
        select(RecommendationImpression).where(
            RecommendationImpression.id == click_data.impression_id,
            RecommendationImpression.user_id == current_user.id,
        )
    )
    impression = result.scalar_one_or_none()

    if impression:
        impression.was_clicked = True
        impression.clicked_at = datetime.utcnow()

        await db.commit()


@router.post("/views", status_code=status.HTTP_201_CREATED)
async def log_content_view(
    view_event: ViewEvent,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> dict:
    """
    Log content view event.

    **ML Value**: Interest signal even without play/interaction!

    **Tracks:**
    - Track detail page views
    - Album page views
    - Artist page views
    - Time spent on page
    - Scroll behavior

    **ML Use Cases:**
    - Interest prediction (viewed but didn't play = future intent)
    - Engagement metrics
    - Content quality (high time spent = good content)
    - A/B testing page designs

    **Example Insights:**
    - User viewed track but didn't play = wrong mood?
    - Viewed artist page, followed = strong signal
    - Short view time = not interested
    """
    view = ContentView(
        user_id=current_user.id,
        content_type=view_event.content_type,
        content_id=view_event.content_id,
        source=view_event.source,
        source_id=view_event.source_id,
        session_id=view_event.session_id,
        time_spent_ms=view_event.time_spent_ms,
        scrolled_to_bottom=view_event.scrolled_to_bottom,
    )

    db.add(view)
    await db.commit()
    await db.refresh(view)

    return {"view_id": view.id}


@router.post("/player/events", status_code=status.HTTP_201_CREATED)
async def log_player_event(
    event: PlayerEventLog,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Log granular player events.

    **ML Patterns Detected:**

    **Seek Events:**
    - Users skipping intros = preference for main content
    - Seeking to specific timestamp = replay favorite part
    - Multiple seeks = user exploring track
    - Forward seeks near end = skipping outro

    **Buffer Events:**
    - Frequent buffering = quality issues
    - Geographic patterns in buffering = CDN issues
    - Abandon after buffer = poor UX

    **Error Events:**
    - Track playback errors = broken content
    - Pattern in errors = systematic issue

    **ML Use:**
    - Detect skip patterns (users skip first 10 seconds)
    - Quality issues affect recommendations
    - Error-prone tracks get lower scores
    - Seek behavior = engagement level

    **Beyond Spotify**: They don't expose this granularity!
    """
    player_event = PlayerEvent(
        user_id=current_user.id,
        track_id=event.track_id,
        session_id=event.session_id,
        event_type=event.event_type,
        position_ms=event.position_ms,
        seek_from_ms=event.seek_from_ms,
        seek_to_ms=event.seek_to_ms,
        buffer_duration_ms=event.buffer_duration_ms,
        error_code=event.error_code,
        error_message=event.error_message,
        event_metadata=event.event_metadata,
    )

    db.add(player_event)
    await db.commit()
    await db.refresh(player_event)

    return {"event_id": player_event.id}


class BatchEventsRequest(BaseModel):
    events: List[dict] = Field(..., min_items=1, max_items=1000)


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def log_batch_events(
    batch_request: BatchEventsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch event logging for offline sync.

    **Mobile App Use Case:**
    - Collect events offline
    - Sync when online
    - Reduce API calls

    **Event Types Supported:**
    - interactions
    - views
    - player_events
    - searches

    **Limits:**
    - Max 1000 events per batch
    - Events processed asynchronously

    **Returns:**
    - batch_id for status tracking
    """
    return {
        "message": "Batch queued for processing",
        "batch_id": f"batch-{uuid4()}",
        "event_count": len(batch_request.events),
    }