from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database import get_db
from models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyWithSecret,
    APIKeyUpdate,
    APIKeyUsageStats,
)
from models.user import User
from middleware.auth import get_current_user, require_scopes

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("/", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyWithSecret:
    """
    Create a new API key for the authenticated user.
    The full API key is only shown once during creation.
    """
    # Generate the key
    full_key, key_hash, key_prefix = APIKey.generate_key()

    # Calculate expiration date
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Validate scopes against user's plan
    # TODO: Check if user's plan allows requested scopes

    # Create the API key
    api_key = APIKey(
        user_id=current_user.id,
        org_id=current_user.org_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_data.name,
        description=key_data.description,
        scopes=key_data.scopes,
        environment=key_data.environment,
        rate_limit_requests_per_minute=key_data.rate_limit_requests_per_minute,
        rate_limit_requests_per_hour=key_data.rate_limit_requests_per_hour,
        rate_limit_requests_per_day=key_data.rate_limit_requests_per_day,
        expires_at=expires_at,
        ip_whitelist=key_data.ip_whitelist,
        metadata=key_data.metadata,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Return response with the full key (only time it's shown)
    response = APIKeyWithSecret.from_orm(api_key)
    response.api_key = full_key

    return response


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    environment: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[APIKeyResponse]:
    """List all API keys for the authenticated user."""
    query = select(APIKey).where(APIKey.user_id == current_user.id)

    if environment:
        query = query.where(APIKey.environment == environment)
    if is_active is not None:
        query = query.where(APIKey.is_active == is_active)

    result = await db.execute(query.order_by(APIKey.created_at.desc()))
    api_keys = result.scalars().all()

    return [APIKeyResponse.from_orm(key) for key in api_keys]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """Get details of a specific API key."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return APIKeyResponse.from_orm(api_key)


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: UUID,
    key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """Update an API key's settings."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Update fields
    update_data = key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)

    api_key.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse.from_orm(api_key)


@router.post("/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """Revoke an API key (cannot be undone)."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()

    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse.from_orm(api_key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete an API key."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await db.delete(api_key)
    await db.commit()


@router.post("/{key_id}/rotate", response_model=APIKeyWithSecret)
async def rotate_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyWithSecret:
    """
    Rotate an API key - creates a new key with the same settings.
    The old key is automatically revoked.
    """
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    old_key = result.scalar_one_or_none()

    if not old_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Generate new key
    full_key, key_hash, key_prefix = APIKey.generate_key()

    # Create new key with same settings
    new_key = APIKey(
        user_id=old_key.user_id,
        org_id=old_key.org_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=f"{old_key.name} (Rotated)",
        description=old_key.description,
        scopes=old_key.scopes,
        environment=old_key.environment,
        rate_limit_requests_per_minute=old_key.rate_limit_requests_per_minute,
        rate_limit_requests_per_hour=old_key.rate_limit_requests_per_hour,
        rate_limit_requests_per_day=old_key.rate_limit_requests_per_day,
        expires_at=old_key.expires_at,
        ip_whitelist=old_key.ip_whitelist,
        metadata=old_key.metadata,
    )

    # Revoke old key
    old_key.is_active = False
    old_key.revoked_at = datetime.utcnow()

    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    # Return response with the full key
    response = APIKeyWithSecret.from_orm(new_key)
    response.api_key = full_key

    return response


@router.get("/{key_id}/usage", response_model=APIKeyUsageStats)
async def get_api_key_usage(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 7,
) -> APIKeyUsageStats:
    """Get usage statistics for an API key."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.id == key_id, APIKey.user_id == current_user.id)
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Calculate period
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)

    # TODO: Query api_key_usage_logs table for detailed stats
    # For now, return basic stats
    return APIKeyUsageStats(
        api_key_id=api_key.id,
        total_requests=api_key.total_requests,
        successful_requests=0,
        failed_requests=0,
        avg_response_time_ms=0.0,
        requests_by_endpoint={},
        requests_by_status_code={},
        period_start=period_start,
        period_end=period_end,
    )