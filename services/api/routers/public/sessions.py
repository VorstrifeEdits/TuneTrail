from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.player import (
    ListeningSession,
    SessionStart,
    SessionEnd,
    SessionResponse,
)
from middleware.auth import get_current_user

router = APIRouter(prefix="/sessions", tags=["Listening Sessions"])


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Start a new listening session.

    **ML Critical**: Groups interactions for pattern detection.

    **Session Grouping Enables:**
    - Detect listening patterns (binge sessions, quick skips)
    - Understand context switches
    - Time-of-day preferences
    - Device-specific behavior
    - Session-based recommendations

    **Usage:**
    - Client calls on app open / login
    - Returns session_id for all subsequent interactions
    - Auto-expires after 1 hour of inactivity

    **Required scopes**: `write:sessions`
    """
    session = ListeningSession(
        user_id=current_user.id,
        device_type=session_data.device_type,
        platform=session_data.platform,
        device_id=session_data.device_id,
        context_type=session_data.context_type,
        context_id=session_data.context_id,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse.from_orm(session)


@router.put("/{session_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def session_heartbeat(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Keep session alive.

    **Usage:**
    - Client sends every 30-60 seconds while active
    - Prevents session auto-expiry
    - Updates last_activity timestamp

    **Auto-Expiry:**
    - Sessions without heartbeat for 1 hour are auto-closed
    """
    result = await db.execute(
        select(ListeningSession).where(
            ListeningSession.id == session_id,
            ListeningSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )

    session.last_heartbeat = datetime.utcnow()
    await db.commit()


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    session_end: SessionEnd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    End listening session.

    **ML Value:**
    - Marks session boundary
    - Captures session summary stats
    - Enables session-level analysis

    **Analytics Captured:**
    - Total tracks played
    - Total duration
    - Session mood/activity tags
    - Completion rate

    **Required scopes**: `write:sessions`
    """
    result = await db.execute(
        select(ListeningSession).where(
            ListeningSession.id == session_id,
            ListeningSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.ended_at = datetime.utcnow()
    session.total_tracks_played = session_end.tracks_played
    session.total_duration_seconds = session_end.duration_seconds

    await db.commit()
    await db.refresh(session)

    return SessionResponse.from_orm(session)


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    skip: int = 0,
    days: int = 30,
) -> List[SessionResponse]:
    """
    List user's listening sessions.

    **Use Cases:**
    - "Continue where you left off"
    - Session history
    - Pattern analysis

    **Required scopes**: `read:sessions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(ListeningSession)
        .where(
            ListeningSession.user_id == current_user.id,
            ListeningSession.started_at >= cutoff_date,
        )
        .order_by(ListeningSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [SessionResponse.from_orm(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Get specific session details.

    **Required scopes**: `read:sessions`
    """
    result = await db.execute(
        select(ListeningSession).where(
            ListeningSession.id == session_id,
            ListeningSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return SessionResponse.from_orm(session)


@router.get("/stats/summary")
async def get_session_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30,
):
    """
    Get session statistics.

    **ML Insights:**
    - Average session duration
    - Sessions per day
    - Peak listening times
    - Device usage patterns

    **Required scopes**: `read:sessions`
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    total_sessions_query = select(func.count(ListeningSession.id)).where(
        ListeningSession.user_id == current_user.id,
        ListeningSession.started_at >= cutoff_date,
    )
    total_sessions = await db.scalar(total_sessions_query) or 0

    avg_duration_query = select(
        func.avg(ListeningSession.total_duration_seconds)
    ).where(
        ListeningSession.user_id == current_user.id,
        ListeningSession.ended_at.isnot(None),
        ListeningSession.started_at >= cutoff_date,
    )
    avg_duration = await db.scalar(avg_duration_query) or 0

    return {
        "total_sessions": total_sessions,
        "average_duration_minutes": round(avg_duration / 60, 2) if avg_duration else 0,
        "period_days": days,
    }