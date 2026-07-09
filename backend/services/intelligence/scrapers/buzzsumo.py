"""BuzzSumo scraper for trending content analysis."""

from __future__ import annotations

import time
from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BuzzSumoScraper(BaseScraper):
    """Scrape BuzzSumo for trending content with social share analysis."""

    source_name = "buzzsumo"
    rate_limit_requests = 10
    rate_limit_window = 60

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.BUZZSUMO_API_KEY
        self._base_url = "https://app.buzzsumo.com/api"

    @scraper_retry
    async def _search_trending_content(
        self,
        query: str = "",
        num_results: int = 50,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Search for trending content by topic."""
        client = await self._get_client()
        params: dict[str, Any] = {
            "api_key": self._api_key,
            "num_results": num_results,
            "sort_by": "total_shares",
        }
        if query:
            params["q"] = query

        begin_date = int(time.time()) - (hours * 3600)
        params["begin_date"] = begin_date

        response = await client.get(
            f"{self._base_url}/search/content.json",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])

    def _calculate_content_velocity(self, article: dict[str, Any]) -> float:
        """Calculate content velocity from shares per time."""
        total_shares = (
            article.get("facebook_shares", 0)
            + article.get("twitter_shares", 0)
            + article.get("pinterest_shares", 0)
            + article.get("reddit_shares", 0)
        )
        published_date = article.get("published_date", 0)
        if published_date:
            age_hours = max((time.time() - published_date) / 3600, 0.1)
        else:
            age_hours = 24.0
        return round(total_shares / age_hours, 2)

    def _article_to_topic(self, article: dict[str, Any]) -> RawTopic:
        """Convert a BuzzSumo article to a RawTopic."""
        velocity = self._calculate_content_velocity(article)
        return RawTopic(
            title=article.get("title", ""),
            description=article.get("description", article.get("title", ""))[:500],
            engagement_metrics={
                "facebook_shares": article.get("facebook_shares", 0),
                "twitter_shares": article.get("twitter_shares", 0),
                "pinterest_shares": article.get("pinterest_shares", 0),
                "reddit_shares": article.get("reddit_shares", 0),
                "total_shares": (
                    article.get("facebook_shares", 0)
                    + article.get("twitter_shares", 0)
                    + article.get("pinterest_shares", 0)
                    + article.get("reddit_shares", 0)
                ),
                "content_velocity": velocity,
                "evergreen_score": article.get("evergreen_score", 0),
            },
            source=self.source_name,
            platform="web",
            url=article.get("url", ""),
            raw_data={
                "author_name": article.get("author_name", ""),
                "domain_name": article.get("domain_name", ""),
                "language": article.get("language", ""),
                "word_count": article.get("word_count", 0),
                "num_linking_domains": article.get("num_linking_domains", 0),
            },
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape BuzzSumo for trending content."""
        await self._check_limit()

        # Fetch general trending content (empty query = trending)
        articles = await self._search_trending_content(query="", num_results=50, hours=24)
        topics = [self._article_to_topic(a) for a in articles]

        topics.sort(
            key=lambda t: t.engagement_metrics.get("content_velocity", 0),
            reverse=True,
        )

        logger.info("buzzsumo_scrape_complete", topic_count=len(topics))
        return topics

    async def health_check(self) -> bool:
        """Check BuzzSumo API access."""
        try:
            if not self._api_key:
                return False
            results = await self._search_trending_content(query="ai", num_results=1)
            return isinstance(results, list)
        except Exception as exc:
            logger.error("buzzsumo_health_fail", error=str(exc))
            return False
