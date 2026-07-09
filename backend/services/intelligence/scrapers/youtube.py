"""YouTube Data API v3 scraper with quota tracking."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Quota costs
_COST_MOST_POPULAR = 1
_COST_VIDEO_DETAILS = 1  # per batch of 50
_DAILY_BUDGET = 10_000


class YouTubeScraper(BaseScraper):
    """Scrape YouTube Data API v3 for trending videos and engagement signals."""

    source_name = "youtube"
    rate_limit_requests = 100
    rate_limit_window = 100  # roughly matches quota pacing

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.YOUTUBE_API_KEY
        self._base_url = "https://www.googleapis.com/youtube/v3"
        self._quota_used = 0

    def _track_quota(self, cost: int) -> None:
        self._quota_used += cost
        if self._quota_used > _DAILY_BUDGET * 0.9:
            logger.warning(
                "youtube_quota_high",
                used=self._quota_used,
                budget=_DAILY_BUDGET,
            )

    @scraper_retry
    async def _fetch_most_popular(self, max_results: int = 50) -> list[dict[str, Any]]:
        """GET videos?chart=mostPopular"""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": "US",
                "maxResults": min(max_results, 50),
                "key": self._api_key,
            },
        )
        response.raise_for_status()
        self._track_quota(_COST_MOST_POPULAR)
        return response.json().get("items", [])

    @scraper_retry
    async def _fetch_video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Batch fetch video details (max 50 per call)."""
        if not video_ids:
            return []

        client = await self._get_client()
        all_items: list[dict[str, Any]] = []

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            response = await client.get(
                f"{self._base_url}/videos",
                params={
                    "part": "snippet,statistics,contentDetails,topicDetails",
                    "id": ",".join(batch),
                    "key": self._api_key,
                },
            )
            response.raise_for_status()
            self._track_quota(_COST_VIDEO_DETAILS)
            all_items.extend(response.json().get("items", []))

        return all_items

    def _calculate_engagement_velocity(self, stats: dict[str, Any]) -> float:
        """Calculate engagement velocity from view, like, and comment counts."""
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        # Weighted engagement score normalised to 0-100
        raw = (views * 0.001) + (likes * 0.1) + (comments * 0.5)
        return min(round(raw, 2), 100.0)

    def _video_to_topic(self, video: dict[str, Any]) -> RawTopic:
        """Convert a YouTube video item to a RawTopic."""
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        velocity = self._calculate_engagement_velocity(stats)

        return RawTopic(
            title=snippet.get("title", ""),
            description=snippet.get("description", "")[:500],
            engagement_metrics={
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "engagement_velocity": velocity,
            },
            source=self.source_name,
            platform="youtube",
            url=f"https://www.youtube.com/watch?v={video.get('id', '')}",
            raw_data={
                "video_id": video.get("id", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "category_id": snippet.get("categoryId", ""),
                "tags": snippet.get("tags", []),
                "published_at": snippet.get("publishedAt", ""),
            },
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape trending YouTube videos."""
        await self._check_limit()

        if self._quota_used >= _DAILY_BUDGET:
            logger.warning("youtube_quota_exhausted", used=self._quota_used)
            return []

        videos = await self._fetch_most_popular(max_results=50)
        topics = [self._video_to_topic(v) for v in videos]

        topics.sort(
            key=lambda t: t.engagement_metrics.get("engagement_velocity", 0),
            reverse=True,
        )

        logger.info(
            "youtube_scrape_complete",
            video_count=len(topics),
            quota_used=self._quota_used,
        )
        return topics

    async def health_check(self) -> bool:
        """Verify YouTube API key is valid."""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self._base_url}/videos",
                params={
                    "part": "id",
                    "chart": "mostPopular",
                    "maxResults": 1,
                    "key": self._api_key,
                },
            )
            return response.status_code == 200
        except Exception as exc:
            logger.error("youtube_health_fail", error=str(exc))
            return False
