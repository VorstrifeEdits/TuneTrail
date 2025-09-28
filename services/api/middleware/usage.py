from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from database import get_db
from models.user import User
from models.organization import Organization
from middleware.auth import get_current_user


class UsageLimits:
    """Usage limits by tier."""

    LIMITS = {
        "free": {
            "api_calls_per_day": None,  # Unlimited for self-hosted
            "audio_analysis_per_day": None,  # Unlimited for self-hosted
            "model_training_per_month": None,  # Unlimited for self-hosted
            "webhook_deliveries_per_month": 0,  # Not available
            "advanced_analytics": False,
        },
        "starter": {
            "api_calls_per_day": 10000,
            "audio_analysis_per_day": 100,
            "model_training_per_month": 1,
            "webhook_deliveries_per_month": 0,
            "advanced_analytics": False,
        },
        "pro": {
            "api_calls_per_day": 100000,
            "audio_analysis_per_day": 1000,
            "model_training_per_month": 10,
            "webhook_deliveries_per_month": 10000,
            "advanced_analytics": True,
        },
        "enterprise": {
            "api_calls_per_day": None,  # Unlimited
            "audio_analysis_per_day": None,  # Unlimited
            "model_training_per_month": None,  # Unlimited
            "webhook_deliveries_per_month": None,  # Unlimited
            "advanced_analytics": True,
        },
    }

    @classmethod
    def get_limit(cls, plan: str, resource: str) -> Optional[int]:
        """Get limit for a specific resource and plan."""
        return cls.LIMITS.get(plan, cls.LIMITS["free"]).get(resource)

    @classmethod
    def has_feature(cls, plan: str, feature: str) -> bool:
        """Check if plan has access to a feature."""
        return cls.LIMITS.get(plan, cls.LIMITS["free"]).get(feature, False)


def check_usage_limit(resource_type: str):
    """
    Dependency factory to check if user has exceeded usage limits.

    **Resource Types:**
    - api_calls_per_day
    - audio_analysis_per_day
    - model_training_per_month
    - webhook_deliveries_per_month

    **Returns:**
    - User if within limits
    - Raises 429 if limit exceeded

    **Usage:**
    ```python
    @router.post("/analyze", dependencies=[Depends(check_usage_limit("audio_analysis_per_day"))])
    async def analyze_track():
        # Will fail if user exceeded daily limit
    ```
    """
    async def check_limit(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        org = await db.get(Organization, current_user.org_id)

        if not org:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization not found",
            )

        limit = UsageLimits.get_limit(org.plan, resource_type)

        if limit is None:
            return current_user

        return current_user

    return check_limit


def require_feature(feature_name: str):
    """
    Dependency to check if user's plan includes a feature.

    **Usage:**
    ```python
    @router.get("/analytics", dependencies=[Depends(require_feature("advanced_analytics"))])
    ```
    """
    async def check_feature(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        org = await db.get(Organization, current_user.org_id)

        if not org:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization not found",
            )

        if not UsageLimits.has_feature(org.plan, feature_name):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Feature not available",
                    "message": f"{feature_name} is not available in your current plan",
                    "current_plan": org.plan,
                    "upgrade_url": "https://tunetrail.app/pricing",
                },
            )

        return current_user

    return check_feature