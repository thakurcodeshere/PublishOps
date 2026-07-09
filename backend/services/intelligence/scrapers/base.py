"""Base scraper ABC — shared interface and utilities for all intelligence scrapers."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.utils.logger import get_logger
from backend.utils.rate_limiter import RateLimitInfo, RateLimiter

logger = get_logger(__name__)


@dataclass
class RawTopic:
    """Normalised topic discovered from any source."""

    title: str
    description: str
    engagement_metrics: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    platform: str = ""
    url: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


# Reusable retry decorator for scraper methods
scraper_retry = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


class BaseScraper(abc.ABC):
    """Abstract base class for all data source scrapers."""

    source_name: str = "unknown"
    rate_limit_requests: int = 60
    rate_limit_window: int = 60  # seconds

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter or RateLimiter()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialise a shared httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "PublishOps/1.0"},
            )
        return self._client

    async def _check_limit(self) -> RateLimitInfo:
        """Check rate limit before making a request."""
        return await self._rate_limiter.check_rate_limit(
            self.source_name,
            self.rate_limit_requests,
            self.rate_limit_window,
        )

    @abc.abstractmethod
    async def scrape(self) -> list[RawTopic]:
        """Scrape the source and return normalised topics."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verify the source is reachable and credentials are valid."""
        ...

    async def get_rate_limit_status(self) -> RateLimitInfo:
        """Return current rate limit status without consuming a token."""
        return await self._rate_limiter.get_status(
            self.source_name,
            self.rate_limit_requests,
            self.rate_limit_window,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
