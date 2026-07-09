"""Pexels scraper for trending visual content and popular searches."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PexelsScraper(BaseScraper):
    """Scrape Pexels API for trending visual content and popular search queries."""

    source_name = "pexels"
    rate_limit_requests = 200
    rate_limit_window = 3600

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.PEXELS_API_KEY
        self._base_url = "https://api.pexels.com"

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": self._api_key}

    @scraper_retry
    async def _fetch_curated_photos(self, per_page: int = 40) -> list[dict[str, Any]]:
        """Fetch curated (trending) photos."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/v1/curated",
            params={"per_page": per_page},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json().get("photos", [])

    @scraper_retry
    async def _fetch_popular_videos(self, per_page: int = 20) -> list[dict[str, Any]]:
        """Fetch popular videos."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/videos/popular",
            params={"per_page": per_page},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json().get("videos", [])

    @scraper_retry
    async def _search_photos(self, query: str, per_page: int = 15) -> list[dict[str, Any]]:
        """Search photos by query to gauge visual trend popularity."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/v1/search",
            params={"query": query, "per_page": per_page},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return data.get("photos", [])

    def _photo_to_topic(self, photo: dict[str, Any]) -> RawTopic:
        """Convert a Pexels photo to a RawTopic based on visual trends."""
        alt_text = photo.get("alt", "Untitled visual content")
        photographer = photo.get("photographer", "Unknown")
        avg_color = photo.get("avg_color", "")

        return RawTopic(
            title=alt_text[:200] if alt_text else "Trending visual content",
            description=f"Trending visual content on Pexels by {photographer}",
            engagement_metrics={
                "source_type": "curated_photo",
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
            },
            source=self.source_name,
            platform="pexels",
            url=photo.get("url", ""),
            raw_data={
                "photo_id": photo.get("id"),
                "photographer": photographer,
                "photographer_url": photo.get("photographer_url", ""),
                "avg_color": avg_color,
                "src": photo.get("src", {}),
            },
        )

    def _video_to_topic(self, video: dict[str, Any]) -> RawTopic:
        """Convert a Pexels video to a RawTopic."""
        user = video.get("user", {})
        duration = video.get("duration", 0)

        video_files = video.get("video_files", [])
        max_quality = ""
        for vf in video_files:
            if vf.get("quality") == "hd":
                max_quality = "HD"
                break
            elif vf.get("quality") == "sd":
                max_quality = "SD"

        return RawTopic(
            title=f"Trending video content ({duration}s)",
            description=f"Popular video on Pexels — {duration}s, {max_quality}",
            engagement_metrics={
                "source_type": "popular_video",
                "duration": duration,
                "quality": max_quality,
            },
            source=self.source_name,
            platform="pexels",
            url=video.get("url", ""),
            raw_data={
                "video_id": video.get("id"),
                "user": user.get("name", ""),
                "width": video.get("width", 0),
                "height": video.get("height", 0),
                "video_pictures": [vp.get("picture") for vp in video.get("video_pictures", [])],
            },
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape Pexels for trending visual content."""
        await self._check_limit()

        all_topics: list[RawTopic] = []

        try:
            photos = await self._fetch_curated_photos(per_page=30)
            for photo in photos:
                all_topics.append(self._photo_to_topic(photo))
        except Exception as exc:
            logger.error("pexels_curated_error", error=str(exc))

        try:
            videos = await self._fetch_popular_videos(per_page=15)
            for video in videos:
                all_topics.append(self._video_to_topic(video))
        except Exception as exc:
            logger.error("pexels_videos_error", error=str(exc))

        # Search for topically trending visual content
        trending_visual_queries = ["technology", "nature", "workspace", "city life"]
        for query in trending_visual_queries:
            try:
                results = await self._search_photos(query, per_page=5)
                for photo in results:
                    topic = self._photo_to_topic(photo)
                    topic.engagement_metrics["search_query"] = query
                    all_topics.append(topic)
            except Exception as exc:
                logger.error("pexels_search_error", query=query, error=str(exc))

        logger.info("pexels_scrape_complete", topic_count=len(all_topics))
        return all_topics

    async def health_check(self) -> bool:
        """Check Pexels API availability."""
        try:
            if not self._api_key:
                return False
            photos = await self._fetch_curated_photos(per_page=1)
            return isinstance(photos, list)
        except Exception as exc:
            logger.error("pexels_health_fail", error=str(exc))
            return False
