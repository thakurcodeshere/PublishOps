"""TikTok scraper using commercial API endpoints with cache fallback."""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_KEY = "publishops:tiktok:trending_cache"
CACHE_TTL = 900  # 15 minutes


class TikTokScraper(BaseScraper):
    """Scrape TikTok commercial endpoints for trending hashtags and video stats."""

    source_name = "tiktok"
    rate_limit_requests = 30
    rate_limit_window = 60

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._access_token = settings.TIKTOK_ACCESS_TOKEN
        self._base_url = "https://open.tiktokapis.com/v2"
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _get_cached_data(self) -> list[dict[str, Any]] | None:
        """Try to fetch cached trending data from Redis."""
        try:
            r = await self._get_redis()
            import json
            data = await r.get(CACHE_KEY)
            if data:
                return json.loads(data)
        except Exception as exc:
            logger.warning("tiktok_cache_read_error", error=str(exc))
        return None

    async def _set_cached_data(self, data: list[dict[str, Any]]) -> None:
        """Cache trending data in Redis."""
        try:
            r = await self._get_redis()
            import json
            await r.setex(CACHE_KEY, CACHE_TTL, json.dumps(data))
        except Exception as exc:
            logger.warning("tiktok_cache_write_error", error=str(exc))

    @scraper_retry
    async def _fetch_trending_hashtags(self) -> list[dict[str, Any]]:
        """Fetch trending hashtags from TikTok Research API."""
        client = await self._get_client()
        response = await client.post(
            f"{self._base_url}/research/hashtag/trending/",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            json={
                "count": 50,
                "cursor": 0,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("hashtags", [])

    @scraper_retry
    async def _fetch_video_stats(self, hashtag: str) -> dict[str, Any]:
        """Aggregate video stats for a specific hashtag."""
        client = await self._get_client()
        response = await client.post(
            f"{self._base_url}/research/video/query/",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            json={
                "query": {"and": [{"operation": "EQ", "field_name": "hashtag_name", "field_values": [hashtag]}]},
                "max_count": 20,
                "start_date": "20240101",
                "end_date": "20261231",
            },
        )
        response.raise_for_status()
        data = response.json()
        videos = data.get("data", {}).get("videos", [])

        total_views = sum(v.get("view_count", 0) for v in videos)
        total_likes = sum(v.get("like_count", 0) for v in videos)
        total_shares = sum(v.get("share_count", 0) for v in videos)
        total_comments = sum(v.get("comment_count", 0) for v in videos)

        return {
            "hashtag": hashtag,
            "video_count": len(videos),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
        }

    def _hashtag_to_topic(self, hashtag_data: dict[str, Any]) -> RawTopic:
        """Convert hashtag data to a RawTopic."""
        name = hashtag_data.get("hashtag", hashtag_data.get("hashtag_name", ""))
        return RawTopic(
            title=f"#{name}" if name else "Unknown Hashtag",
            description=f"Trending TikTok hashtag #{name} with {hashtag_data.get('video_count', 0)} recent videos",
            engagement_metrics={
                "video_count": hashtag_data.get("video_count", 0),
                "total_views": hashtag_data.get("total_views", 0),
                "total_likes": hashtag_data.get("total_likes", 0),
                "total_shares": hashtag_data.get("total_shares", 0),
                "total_comments": hashtag_data.get("total_comments", 0),
            },
            source=self.source_name,
            platform="tiktok",
            url=f"https://www.tiktok.com/tag/{name}",
            raw_data=hashtag_data,
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape TikTok trending hashtags and aggregate video stats."""
        await self._check_limit()

        topics: list[RawTopic] = []

        try:
            hashtags_raw = await self._fetch_trending_hashtags()

            enriched: list[dict[str, Any]] = []
            for h in hashtags_raw[:20]:
                name = h.get("hashtag_name", h.get("hashtag", ""))
                if not name:
                    continue
                try:
                    stats = await self._fetch_video_stats(name)
                    enriched.append(stats)
                except Exception as exc:
                    logger.warning("tiktok_stats_error", hashtag=name, error=str(exc))
                    enriched.append({"hashtag": name, "video_count": 0})

            await self._set_cached_data(enriched)
            topics = [self._hashtag_to_topic(h) for h in enriched]

        except Exception as exc:
            logger.warning("tiktok_api_error_using_cache", error=str(exc))
            cached = await self._get_cached_data()
            if cached:
                topics = [self._hashtag_to_topic(h) for h in cached]
                logger.info("tiktok_using_cached_data", count=len(topics))
            else:
                logger.error("tiktok_no_cache_available")

        topics.sort(
            key=lambda t: t.engagement_metrics.get("total_views", 0),
            reverse=True,
        )

        logger.info("tiktok_scrape_complete", topic_count=len(topics))
        return topics

    async def health_check(self) -> bool:
        """Check TikTok API availability."""
        try:
            if not self._access_token:
                return False
            await self._fetch_trending_hashtags()
            return True
        except Exception as exc:
            logger.error("tiktok_health_fail", error=str(exc))
            cached = await self._get_cached_data()
            return cached is not None
