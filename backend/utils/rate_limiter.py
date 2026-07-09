"""Redis-backed rate limiter using a sliding-window token bucket algorithm."""

from __future__ import annotations

import time

import redis.asyncio as redis

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, api_name: str, retry_after: float) -> None:
        self.api_name = api_name
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {api_name}. Retry after {retry_after:.1f}s"
        )


class RateLimitInfo:
    """Current rate limit status for an API."""

    def __init__(
        self,
        api_name: str,
        remaining: int,
        limit: int,
        reset_at: float,
    ) -> None:
        self.api_name = api_name
        self.remaining = remaining
        self.limit = limit
        self.reset_at = reset_at

    @property
    def is_limited(self) -> bool:
        return self.remaining <= 0

    @property
    def retry_after(self) -> float:
        return max(0.0, self.reset_at - time.time())


class RateLimiter:
    """Token bucket rate limiter backed by Redis for distributed coordination."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis: redis.Redis | None = redis_client

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        return self._redis

    def _key(self, api_name: str) -> str:
        return f"publishops:ratelimit:{api_name}"

    async def check_rate_limit(
        self,
        api_name: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitInfo:
        """
        Check and consume one token from the rate limit bucket.

        Uses a Redis sorted set with timestamps as scores to implement
        a sliding window rate limiter.

        Raises RateLimitExceeded if the limit is exceeded.
        """
        r = await self._get_redis()
        key = self._key(api_name)
        now = time.time()
        window_start = now - window_seconds

        pipe = r.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count current entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {f"{now}": now})
        # Set TTL on the key
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()

        current_count = results[1]  # zcard result before adding

        if current_count >= max_requests:
            # Find earliest entry to calculate retry_after
            earliest = await r.zrange(key, 0, 0, withscores=True)
            retry_after = (
                (earliest[0][1] + window_seconds - now) if earliest else window_seconds
            )
            # Remove the entry we just added since we're rejecting
            await r.zrem(key, f"{now}")
            logger.warning(
                "rate_limit_exceeded",
                api_name=api_name,
                current_count=current_count,
                max_requests=max_requests,
                retry_after=retry_after,
            )
            raise RateLimitExceeded(api_name, retry_after)

        remaining = max_requests - current_count - 1
        reset_at = now + window_seconds

        return RateLimitInfo(
            api_name=api_name,
            remaining=remaining,
            limit=max_requests,
            reset_at=reset_at,
        )

    async def get_status(
        self,
        api_name: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitInfo:
        """Get current rate limit status without consuming a token."""
        r = await self._get_redis()
        key = self._key(api_name)
        now = time.time()
        window_start = now - window_seconds

        await r.zremrangebyscore(key, "-inf", window_start)
        current_count: int = await r.zcard(key)

        remaining = max(0, max_requests - current_count)
        reset_at = now + window_seconds

        return RateLimitInfo(
            api_name=api_name,
            remaining=remaining,
            limit=max_requests,
            reset_at=reset_at,
        )

    async def reset(self, api_name: str) -> None:
        """Reset rate limit for an API."""
        r = await self._get_redis()
        await r.delete(self._key(api_name))
        logger.info("rate_limit_reset", api_name=api_name)

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
