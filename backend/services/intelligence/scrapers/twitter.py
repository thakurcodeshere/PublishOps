"""Twitter / X scraper using v2 API with aggressive Redis caching."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_PREFIX = "publishops:twitter"
CACHE_TTL = 900  # 15-minute TTL to minimise paid API calls


class TwitterScraper(BaseScraper):
    """Scrape Twitter v2 API for trending topics with aggressive caching."""

    source_name = "twitter"
    rate_limit_requests = 15
    rate_limit_window = 900  # 15 minutes (matches Twitter's window)

    def __init__(self, woeid: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._bearer_token = settings.TWITTER_BEARER_TOKEN
        self._woeid = woeid  # 1 = Worldwide
        self._base_url = "https://api.twitter.com"
        self._redis_client: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis_client is None:
            settings = get_settings()
            self._redis_client = redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        return self._redis_client

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._bearer_token}"}

    async def _get_cached(self, key: str) -> Any | None:
        try:
            r = await self._get_redis()
            data = await r.get(f"{CACHE_PREFIX}:{key}")
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cached(self, key: str, data: Any) -> None:
        try:
            r = await self._get_redis()
            await r.setex(f"{CACHE_PREFIX}:{key}", CACHE_TTL, json.dumps(data))
        except Exception as exc:
            logger.warning("twitter_cache_set_error", error=str(exc))

    @scraper_retry
    async def _fetch_trends(self) -> list[dict[str, Any]]:
        """Fetch trending topics by WOEID using Twitter v1.1 trends endpoint."""
        cache_key = f"trends:{self._woeid}"
        cached = await self._get_cached(cache_key)
        if cached:
            logger.info("twitter_trends_from_cache", woeid=self._woeid)
            return cached

        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/1.1/trends/place.json",
            params={"id": self._woeid},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()

        trends = data[0].get("trends", []) if data else []
        await self._set_cached(cache_key, trends)
        return trends

    @scraper_retry
    async def _search_recent_tweets(
        self, query: str, max_results: int = 10
    ) -> dict[str, Any]:
        """Search recent tweets for engagement metrics."""
        cache_key = f"search:{query}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/2/tweets/search/recent",
            params={
                "query": query,
                "max_results": max_results,
                "tweet.fields": "public_metrics,created_at,author_id",
            },
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        await self._set_cached(cache_key, data)
        return data

    def _trend_to_topic(
        self, trend: dict[str, Any], engagement: dict[str, Any]
    ) -> RawTopic:
        """Convert a Twitter trend to a RawTopic."""
        name = trend.get("name", "")
        tweet_volume = trend.get("tweet_volume") or 0

        tweets = engagement.get("data", [])
        total_likes = sum(
            t.get("public_metrics", {}).get("like_count", 0) for t in tweets
        )
        total_retweets = sum(
            t.get("public_metrics", {}).get("retweet_count", 0) for t in tweets
        )
        total_replies = sum(
            t.get("public_metrics", {}).get("reply_count", 0) for t in tweets
        )

        return RawTopic(
            title=name,
            description=f"Trending on Twitter/X with {tweet_volume:,} tweets" if tweet_volume else f"Trending on Twitter/X: {name}",
            engagement_metrics={
                "tweet_volume": tweet_volume,
                "sample_likes": total_likes,
                "sample_retweets": total_retweets,
                "sample_replies": total_replies,
                "sample_size": len(tweets),
            },
            source=self.source_name,
            platform="twitter",
            url=trend.get("url", f"https://twitter.com/search?q={name}"),
            raw_data={
                "query": trend.get("query", ""),
                "promoted_content": trend.get("promoted_content"),
            },
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape Twitter trends with engagement sampling."""
        await self._check_limit()

        trends = await self._fetch_trends()
        topics: list[RawTopic] = []

        for trend in trends[:30]:
            name = trend.get("name", "")
            if not name:
                continue
            try:
                engagement = await self._search_recent_tweets(name, max_results=10)
            except Exception as exc:
                logger.warning("twitter_search_error", trend=name, error=str(exc))
                engagement = {}

            topics.append(self._trend_to_topic(trend, engagement))

        topics.sort(
            key=lambda t: t.engagement_metrics.get("tweet_volume", 0),
            reverse=True,
        )

        logger.info("twitter_scrape_complete", topic_count=len(topics))
        return topics

    async def health_check(self) -> bool:
        """Verify Twitter bearer token is valid."""
        try:
            if not self._bearer_token:
                return False
            client = await self._get_client()
            response = await client.get(
                f"{self._base_url}/2/tweets/search/recent",
                params={"query": "test", "max_results": 10},
                headers=self._auth_headers(),
            )
            return response.status_code == 200
        except Exception as exc:
            logger.error("twitter_health_fail", error=str(exc))
            return False
