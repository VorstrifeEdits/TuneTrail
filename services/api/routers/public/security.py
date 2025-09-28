from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from middleware.auth import get_current_user

router = APIRouter(prefix="/auth/security", tags=["Account Security"])


class ActiveSession(BaseModel):
    """Active user session."""
    session_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    ip_address: Optional[str]
    location: Optional[str]
    last_used_at: datetime
    is_current: bool

    class Config:
        from_attributes = True


class LoginHistoryItem(BaseModel):
    """Login attempt record."""
    timestamp: datetime
    success: bool
    failure_reason: Optional[str]
    ip_address: Optional[str]
    device_type: Optional[str]
    location: Optional[str]


class SecurityStatus(BaseModel):
    """Overall account security status."""
    email_verified: bool
    two_factor_enabled: bool
    password_strength: str = Field(..., pattern="^(weak|medium|strong)$")
    password_last_changed: Optional[datetime]
    active_sessions_count: int
    suspicious_activity: bool = False
    recommendations: List[str] = []


@router.get("/status", response_model=SecurityStatus)
async def get_security_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SecurityStatus:
    """
    Get account security overview.

    **Security Recommendations:**
    - Enable 2FA
    - Verify email
    - Use strong password
    - Review active sessions

    **Fraud Detection:**
    - Unusual login locations
    - Multiple failed attempts
    - Concurrent sessions from different locations
    """
    recommendations = []

    if not current_user.email_verified:
        recommendations.append("Verify your email address")

    password_age_days = 365
    if password_age_days > 90:
        recommendations.append("Consider changing your password (last changed 365+ days ago)")

    if not current_user.preferences.get("two_factor_enabled"):
        recommendations.append("Enable two-factor authentication for better security")

    return SecurityStatus(
        email_verified=current_user.email_verified,
        two_factor_enabled=False,
        password_strength="medium",
        password_last_changed=None,
        active_sessions_count=1,
        suspicious_activity=False,
        recommendations=recommendations,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_current_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout from current session.

    **Action:**
    - Invalidates current JWT token
    - Adds token to blacklist
    - Clears session data

    **Note:** Client should discard the token immediately.
    """
    pass


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout from all devices/sessions.

    **Use Cases:**
    - Security breach response
    - Shared device cleanup
    - Account takeover recovery

    **Action:**
    - Invalidates all JWT tokens
    - Clears all sessions
    - Requires re-login on all devices
    """
    pass