"""SerpAPI scraper for Google SERP analysis and People Also Ask extraction."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SerpAPIScraper(BaseScraper):
    """Scrape SerpAPI for Google SERP results, PAA, and related searches."""

    source_name = "serpapi"
    rate_limit_requests = 100
    rate_limit_window = 3600

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.SERPAPI_KEY
        self._base_url = "https://serpapi.com/search.json"

    @scraper_retry
    async def _search(self, query: str) -> dict[str, Any]:
        """Execute a Google search via SerpAPI."""
        client = await self._get_client()
        response = await client.get(
            self._base_url,
            params={
                "q": query,
                "api_key": self._api_key,
                "engine": "google",
                "gl": "us",
                "hl": "en",
                "num": 20,
            },
        )
        response.raise_for_status()
        return response.json()

    def _extract_paa(self, serp_data: dict[str, Any]) -> list[RawTopic]:
        """Extract 'People Also Ask' questions as topics."""
        paa_list = serp_data.get("related_questions", [])
        topics: list[RawTopic] = []
        for paa in paa_list:
            question = paa.get("question", "")
            if not question:
                continue
            topics.append(
                RawTopic(
                    title=question,
                    description=paa.get("snippet", question),
                    engagement_metrics={
                        "source_type": "people_also_ask",
                        "has_featured_snippet": True,
                    },
                    source=self.source_name,
                    platform="google",
                    url=paa.get("link", ""),
                    raw_data={
                        "displayed_link": paa.get("displayed_link", ""),
                        "source_title": paa.get("title", ""),
                    },
                )
            )
        return topics

    def _extract_related_searches(self, serp_data: dict[str, Any]) -> list[RawTopic]:
        """Extract related searches as potential topics."""
        related = serp_data.get("related_searches", [])
        topics: list[RawTopic] = []
        for item in related:
            query = item.get("query", "")
            if not query:
                continue
            topics.append(
                RawTopic(
                    title=query,
                    description=f"Related Google search: {query}",
                    engagement_metrics={
                        "source_type": "related_search",
                    },
                    source=self.source_name,
                    platform="google",
                    url=item.get("link", f"https://www.google.com/search?q={query}"),
                    raw_data={"block_position": item.get("block_position")},
                )
            )
        return topics

    def _extract_organic_topics(self, serp_data: dict[str, Any]) -> list[RawTopic]:
        """Extract organic results as topic indicators."""
        results = serp_data.get("organic_results", [])
        topics: list[RawTopic] = []
        for result in results[:10]:
            title = result.get("title", "")
            if not title:
                continue
            topics.append(
                RawTopic(
                    title=title,
                    description=result.get("snippet", "")[:500],
                    engagement_metrics={
                        "position": result.get("position", 0),
                        "source_type": "organic_result",
                        "displayed_link": result.get("displayed_link", ""),
                    },
                    source=self.source_name,
                    platform="google",
                    url=result.get("link", ""),
                    raw_data={
                        "cached_page_link": result.get("cached_page_link"),
                        "rich_snippet": result.get("rich_snippet"),
                        "date": result.get("date"),
                    },
                )
            )
        return topics

    async def scrape(self) -> list[RawTopic]:
        """Scrape Google SERP for trending analysis."""
        await self._check_limit()

        seed_queries = [
            "trending topics today",
            "viral content this week",
            "what's trending right now",
        ]

        all_topics: list[RawTopic] = []

        for query in seed_queries:
            try:
                serp_data = await self._search(query)
                all_topics.extend(self._extract_paa(serp_data))
                all_topics.extend(self._extract_related_searches(serp_data))
                all_topics.extend(self._extract_organic_topics(serp_data))
            except Exception as exc:
                logger.error("serpapi_query_error", query=query, error=str(exc))

        logger.info("serpapi_scrape_complete", topic_count=len(all_topics))
        return all_topics

    async def health_check(self) -> bool:
        """Check SerpAPI availability."""
        try:
            if not self._api_key:
                return False
            client = await self._get_client()
            response = await client.get(
                "https://serpapi.com/account.json",
                params={"api_key": self._api_key},
            )
            return response.status_code == 200
        except Exception as exc:
            logger.error("serpapi_health_fail", error=str(exc))
            return False
