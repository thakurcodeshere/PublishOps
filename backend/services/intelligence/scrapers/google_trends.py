"""Google Trends scraper using pytrends."""

from __future__ import annotations

import asyncio
from typing import Any

from pytrends.request import TrendReq

from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleTrendsScraper(BaseScraper):
    """Scrape Google Trends for daily trends, interest over time, and related queries."""

    source_name = "google_trends"
    rate_limit_requests = 10
    rate_limit_window = 60

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pytrends = TrendReq(hl="en-US", tz=360, retries=3, backoff_factor=1.5)

    def _build_raw_topic(
        self, title: str, description: str, metrics: dict[str, Any], raw: dict[str, Any]
    ) -> RawTopic:
        return RawTopic(
            title=title,
            description=description,
            engagement_metrics=metrics,
            source=self.source_name,
            platform="google",
            url=f"https://trends.google.com/trends/explore?q={title.replace(' ', '+')}",
            raw_data=raw,
        )

    async def _get_trending_searches(self) -> list[RawTopic]:
        """Fetch daily trending searches."""

        def _sync_fetch() -> list[dict[str, Any]]:
            df = self._pytrends.trending_searches(pn="united_states")
            results: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                keyword = str(row[0])
                results.append({"keyword": keyword})
            return results

        try:
            results = await asyncio.to_thread(_sync_fetch)
            topics: list[RawTopic] = []
            for item in results[:30]:
                keyword = item["keyword"]
                topics.append(
                    self._build_raw_topic(
                        title=keyword,
                        description=f"Trending search on Google: {keyword}",
                        metrics={"trending_rank": results.index(item) + 1},
                        raw=item,
                    )
                )
            return topics
        except Exception as exc:
            logger.error("google_trends_trending_error", error=str(exc))
            return []

    async def _get_interest_over_time(self, keywords: list[str]) -> dict[str, float]:
        """Get velocity (interest change) for given keywords."""

        def _sync_fetch() -> dict[str, float]:
            if not keywords:
                return {}
            batch = keywords[:5]  # pytrends supports max 5 at a time
            self._pytrends.build_payload(batch, timeframe="now 7-d")
            df = self._pytrends.interest_over_time()
            velocities: dict[str, float] = {}
            if df.empty:
                return velocities
            for kw in batch:
                if kw in df.columns:
                    values = df[kw].values
                    if len(values) >= 2:
                        recent = float(values[-1])
                        earlier = float(values[0])
                        velocity = (recent - earlier) / max(earlier, 1) * 100
                        velocities[kw] = velocity
                    else:
                        velocities[kw] = 0.0
            return velocities

        try:
            return await asyncio.to_thread(_sync_fetch)
        except Exception as exc:
            logger.error("google_trends_interest_error", error=str(exc))
            return {}

    async def _get_related_queries(self, keyword: str) -> list[str]:
        """Get related queries for topic expansion."""

        def _sync_fetch() -> list[str]:
            self._pytrends.build_payload([keyword], timeframe="now 7-d")
            related = self._pytrends.related_queries()
            queries: list[str] = []
            kw_data = related.get(keyword, {})
            top_df = kw_data.get("top")
            if top_df is not None and not top_df.empty:
                for _, row in top_df.head(10).iterrows():
                    queries.append(str(row["query"]))
            rising_df = kw_data.get("rising")
            if rising_df is not None and not rising_df.empty:
                for _, row in rising_df.head(10).iterrows():
                    queries.append(str(row["query"]))
            return queries

        try:
            return await asyncio.to_thread(_sync_fetch)
        except Exception as exc:
            logger.error("google_trends_related_error", error=str(exc), keyword=keyword)
            return []

    @scraper_retry
    async def scrape(self) -> list[RawTopic]:
        """Run full Google Trends scrape pipeline."""
        await self._check_limit()

        topics = await self._get_trending_searches()

        if topics:
            keywords = [t.title for t in topics[:5]]
            velocities = await self._get_interest_over_time(keywords)
            for topic in topics:
                if topic.title in velocities:
                    topic.engagement_metrics["velocity"] = velocities[topic.title]

            if topics:
                related = await self._get_related_queries(topics[0].title)
                for rel_query in related[:5]:
                    topics.append(
                        self._build_raw_topic(
                            title=rel_query,
                            description=f"Related to trending topic: {topics[0].title}",
                            metrics={"source_type": "related_query"},
                            raw={"parent_topic": topics[0].title},
                        )
                    )

        logger.info("google_trends_scrape_complete", topic_count=len(topics))
        return topics

    async def health_check(self) -> bool:
        """Check if Google Trends is accessible."""
        try:
            result = await asyncio.to_thread(
                self._pytrends.trending_searches, pn="united_states"
            )
            return not result.empty
        except Exception as exc:
            logger.error("google_trends_health_fail", error=str(exc))
            return False
