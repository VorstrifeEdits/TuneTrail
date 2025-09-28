from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status
from redis import Redis
import json


class RateLimiter:
    """
    Token bucket rate limiter using Redis.
    Supports multiple time windows (per minute, hour, day).
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limits: dict[str, int],
        identifier: str = "default",
    ) -> tuple[bool, Optional[dict]]:
        """
        Check if request is within rate limits.

        Args:
            key: API key or user identifier
            limits: Dict with rate limits, e.g. {"minute": 60, "hour": 1000, "day": 10000}
            identifier: Additional identifier (e.g., endpoint name)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = datetime.utcnow()
        is_allowed = True
        rate_limit_info = {}

        for window, limit in limits.items():
            # Create Redis key for this window
            if window == "minute":
                window_key = f"rate_limit:{key}:{identifier}:minute:{now.strftime('%Y%m%d%H%M')}"
                ttl = 60
            elif window == "hour":
                window_key = f"rate_limit:{key}:{identifier}:hour:{now.strftime('%Y%m%d%H')}"
                ttl = 3600
            elif window == "day":
                window_key = f"rate_limit:{key}:{identifier}:day:{now.strftime('%Y%m%d')}"
                ttl = 86400
            else:
                continue

            # Get current count
            current = self.redis.get(window_key)
            current_count = int(current) if current else 0

            # Calculate remaining
            remaining = max(0, limit - current_count)

            # Check if limit exceeded
            if current_count >= limit:
                is_allowed = False

            # Store info
            rate_limit_info[window] = {
                "limit": limit,
                "remaining": remaining,
                "reset_at": self._get_reset_time(now, window),
            }

            # Increment counter if allowed
            if is_allowed:
                pipe = self.redis.pipeline()
                pipe.incr(window_key)
                pipe.expire(window_key, ttl)
                pipe.execute()

        return is_allowed, rate_limit_info

    def _get_reset_time(self, now: datetime, window: str) -> datetime:
        """Calculate when the rate limit window resets."""
        if window == "minute":
            return (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        elif window == "hour":
            return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        elif window == "day":
            return (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        return now

    async def get_rate_limit_status(
        self, key: str, identifier: str = "default"
    ) -> dict:
        """Get current rate limit status without incrementing."""
        now = datetime.utcnow()
        status_info = {}

        for window in ["minute", "hour", "day"]:
            if window == "minute":
                window_key = f"rate_limit:{key}:{identifier}:minute:{now.strftime('%Y%m%d%H%M')}"
            elif window == "hour":
                window_key = f"rate_limit:{key}:{identifier}:hour:{now.strftime('%Y%m%d%H')}"
            elif window == "day":
                window_key = f"rate_limit:{key}:{identifier}:day:{now.strftime('%Y%m%d')}"

            current = self.redis.get(window_key)
            current_count = int(current) if current else 0

            status_info[window] = {
                "current": current_count,
                "reset_at": self._get_reset_time(now, window).isoformat(),
            }

        return status_info


async def enforce_rate_limit(
    request: Request,
    api_key: "APIKey",
    rate_limiter: RateLimiter,
) -> None:
    """
    Middleware function to enforce rate limits on API requests.

    Raises:
        HTTPException: 429 if rate limit is exceeded
    """
    limits = {
        "minute": api_key.rate_limit_requests_per_minute,
        "hour": api_key.rate_limit_requests_per_hour,
        "day": api_key.rate_limit_requests_per_day,
    }

    endpoint = request.url.path
    is_allowed, rate_limit_info = await rate_limiter.check_rate_limit(
        key=str(api_key.id), limits=limits, identifier=endpoint
    )

    # Add rate limit headers to response
    if rate_limit_info.get("minute"):
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(rate_limit_info["minute"]["limit"]),
            "X-RateLimit-Remaining": str(rate_limit_info["minute"]["remaining"]),
            "X-RateLimit-Reset": rate_limit_info["minute"]["reset_at"].isoformat(),
        }

    if not is_allowed:
        # Find which limit was exceeded
        exceeded_window = None
        reset_at = None
        for window, info in rate_limit_info.items():
            if info["remaining"] == 0:
                exceeded_window = window
                reset_at = info["reset_at"]
                break

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "window": exceeded_window,
                "reset_at": reset_at.isoformat() if reset_at else None,
                "rate_limit_info": rate_limit_info,
            },
            headers={
                "Retry-After": str(
                    int((reset_at - datetime.utcnow()).total_seconds())
                    if reset_at
                    else 60
                ),
            },
        )


class IPRateLimiter:
    """Simple IP-based rate limiter for public endpoints."""

    def __init__(self, redis_client: Redis, requests_per_minute: int = 100) -> None:
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute

    async def check_ip_rate_limit(self, ip_address: str) -> bool:
        """Check if IP is within rate limit."""
        now = datetime.utcnow()
        key = f"ip_rate_limit:{ip_address}:{now.strftime('%Y%m%d%H%M')}"

        current = self.redis.get(key)
        current_count = int(current) if current else 0

        if current_count >= self.requests_per_minute:
            return False

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        pipe.execute()

        return True