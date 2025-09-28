from typing import List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.organization import Organization
from middleware.auth import get_current_user


class PlanTier:
    """Plan tier constants."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    ALL_TIERS = [FREE, STARTER, PRO, ENTERPRISE]
    PAID_TIERS = [STARTER, PRO, ENTERPRISE]
    PREMIUM_TIERS = [PRO, ENTERPRISE]


def require_plan(required_plans: List[str]):
    """
    Dependency to enforce plan requirements on endpoints.

    **Usage:**
    ```python
    @router.get("/premium-feature", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
    async def premium_endpoint():
        # Only accessible to Pro and Enterprise users
    ```

    **Error Response:**
    - 402 Payment Required if user's plan not in required_plans
    - Includes upgrade URL and current plan info

    **Examples:**
    - Community-only features: require_plan(["free"])
    - Starter+: require_plan(["starter", "pro", "enterprise"])
    - Pro only: require_plan(["pro", "enterprise"])
    - Enterprise only: require_plan(["enterprise"])
    """
    async def check_plan(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.get(Organization, current_user.org_id)
        org = result

        if not org:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization not found",
            )

        if org.plan not in required_plans:
            required_plans_str = ", ".join(required_plans)

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Plan upgrade required",
                    "message": f"This feature requires one of: {required_plans_str}",
                    "current_plan": org.plan,
                    "required_plans": required_plans,
                    "upgrade_url": "https://tunetrail.app/pricing",
                },
            )

        return current_user

    return check_plan


async def get_user_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Get user's organization (for plan checking)."""
    org = await db.get(Organization, current_user.org_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization not found",
        )

    return org