"""NewsAPI scraper for breaking and topic-specific news."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NewsAPIScraper(BaseScraper):
    """Scrape NewsAPI for breaking news and topic-specific content."""

    source_name = "newsapi"
    rate_limit_requests = 100
    rate_limit_window = 86400  # 100 requests/day on free tier

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.NEWSAPI_KEY
        self._base_url = "https://newsapi.org/v2"

    @scraper_retry
    async def _fetch_top_headlines(
        self, country: str = "us", page_size: int = 50
    ) -> list[dict[str, Any]]:
        """GET /v2/top-headlines for breaking news."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/top-headlines",
            params={
                "country": country,
                "pageSize": page_size,
                "apiKey": self._api_key,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])

    @scraper_retry
    async def _fetch_everything(
        self,
        query: str,
        sort_by: str = "popularity",
        page_size: int = 30,
    ) -> list[dict[str, Any]]:
        """GET /v2/everything for topic-specific news."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/everything",
            params={
                "q": query,
                "sortBy": sort_by,
                "pageSize": page_size,
                "language": "en",
                "apiKey": self._api_key,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])

    def _article_to_topic(self, article: dict[str, Any]) -> RawTopic:
        """Convert a NewsAPI article to a RawTopic."""
        source_name = article.get("source", {}).get("name", "unknown")
        title = article.get("title", "")
        description = article.get("description", "") or ""

        # Estimate engagement from source prominence
        prominent_sources = {
            "BBC News", "CNN", "The New York Times", "Reuters",
            "The Washington Post", "The Guardian", "TechCrunch",
            "The Verge", "Wired", "Bloomberg",
        }
        prominence_score = 80 if source_name in prominent_sources else 40

        return RawTopic(
            title=title,
            description=description[:500],
            engagement_metrics={
                "source_prominence": prominence_score,
                "has_image": bool(article.get("urlToImage")),
                "estimated_reach": prominence_score * 1000,
            },
            source=self.source_name,
            platform="news",
            url=article.get("url", ""),
            raw_data={
                "source_name": source_name,
                "source_id": article.get("source", {}).get("id"),
                "author": article.get("author", ""),
                "published_at": article.get("publishedAt", ""),
                "image_url": article.get("urlToImage", ""),
            },
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape NewsAPI for top headlines and trending topics."""
        await self._check_limit()

        all_topics: list[RawTopic] = []

        # Fetch top headlines
        try:
            headlines = await self._fetch_top_headlines(page_size=50)
            for article in headlines:
                if article.get("title") and article["title"] != "[Removed]":
                    all_topics.append(self._article_to_topic(article))
        except Exception as exc:
            logger.error("newsapi_headlines_error", error=str(exc))

        # Fetch trending tech/science content
        for query in ["artificial intelligence", "technology trends"]:
            try:
                articles = await self._fetch_everything(query=query, page_size=20)
                for article in articles:
                    if article.get("title") and article["title"] != "[Removed]":
                        all_topics.append(self._article_to_topic(article))
            except Exception as exc:
                logger.error("newsapi_everything_error", query=query, error=str(exc))

        all_topics.sort(
            key=lambda t: t.engagement_metrics.get("source_prominence", 0),
            reverse=True,
        )

        logger.info("newsapi_scrape_complete", topic_count=len(all_topics))
        return all_topics

    async def health_check(self) -> bool:
        """Check NewsAPI accessibility."""
        try:
            if not self._api_key:
                return False
            results = await self._fetch_top_headlines(page_size=1)
            return isinstance(results, list)
        except Exception as exc:
            logger.error("newsapi_health_fail", error=str(exc))
            return False
