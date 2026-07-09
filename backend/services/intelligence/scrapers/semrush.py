"""SEMrush scraper for keyword overview and topic research."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SEMrushScraper(BaseScraper):
    """Scrape SEMrush API for keyword data and topic research."""

    source_name = "semrush"
    rate_limit_requests = 40
    rate_limit_window = 60

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = settings.SEMRUSH_API_KEY
        self._base_url = "https://api.semrush.com"

    @scraper_retry
    async def _keyword_overview(self, keyword: str, database: str = "us") -> dict[str, Any]:
        """Get keyword overview: search volume, difficulty, trend."""
        client = await self._get_client()
        response = await client.get(
            self._base_url,
            params={
                "type": "phrase_all",
                "key": self._api_key,
                "phrase": keyword,
                "database": database,
                "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
            },
        )
        response.raise_for_status()
        text = response.text.strip()

        # Parse SEMrush semicolon-delimited response
        lines = text.split("\n")
        if len(lines) < 2:
            return {}

        headers = lines[0].split(";")
        values = lines[1].split(";")
        result: dict[str, Any] = {}
        for h, v in zip(headers, values, strict=False):
            h = h.strip()
            v = v.strip()
            if h == "Keyword":
                result["keyword"] = v
            elif h == "Search Volume":
                result["search_volume"] = int(v) if v.isdigit() else 0
            elif h == "CPC":
                result["cpc"] = float(v) if v.replace(".", "", 1).isdigit() else 0.0
            elif h == "Competition":
                result["competition"] = float(v) if v.replace(".", "", 1).isdigit() else 0.0
            elif h == "Number of Results":
                result["num_results"] = int(v) if v.isdigit() else 0
            elif h == "Trends":
                result["trend"] = v

        return result

    @scraper_retry
    async def _topic_research(self, topic: str) -> list[dict[str, Any]]:
        """Use SEMrush topic research for content ideas."""
        client = await self._get_client()
        response = await client.get(
            f"{self._base_url}/analytics/ta/api/v3/overview",
            params={
                "key": self._api_key,
                "target": topic,
                "export_columns": "topic,volume,difficulty,efficiency",
                "limit": 20,
            },
        )
        response.raise_for_status()
        text = response.text.strip()

        lines = text.split("\n")
        if len(lines) < 2:
            return []

        headers = [h.strip() for h in lines[0].split(";")]
        results: list[dict[str, Any]] = []
        for line in lines[1:]:
            values = [v.strip() for v in line.split(";")]
            row: dict[str, Any] = {}
            for h, v in zip(headers, values, strict=False):
                row[h.lower()] = v
            results.append(row)

        return results

    def _keyword_data_to_topic(self, kw_data: dict[str, Any]) -> RawTopic:
        """Convert keyword data to a RawTopic."""
        keyword = kw_data.get("keyword", "")
        search_volume = kw_data.get("search_volume", 0)
        competition = kw_data.get("competition", 0.0)

        return RawTopic(
            title=keyword,
            description=f"Keyword: {keyword} — Volume: {search_volume:,}, Competition: {competition:.2f}",
            engagement_metrics={
                "search_volume": search_volume,
                "cpc": kw_data.get("cpc", 0.0),
                "competition": competition,
                "num_results": kw_data.get("num_results", 0),
            },
            source=self.source_name,
            platform="search",
            url=f"https://www.google.com/search?q={keyword}",
            raw_data=kw_data,
        )

    async def scrape(self) -> list[RawTopic]:
        """Scrape SEMrush for keyword and topic data."""
        await self._check_limit()

        seed_keywords = [
            "artificial intelligence",
            "content creation",
            "social media trends",
            "productivity tools",
            "remote work",
        ]

        all_topics: list[RawTopic] = []

        for keyword in seed_keywords:
            try:
                kw_data = await self._keyword_overview(keyword)
                if kw_data:
                    all_topics.append(self._keyword_data_to_topic(kw_data))
            except Exception as exc:
                logger.error("semrush_keyword_error", keyword=keyword, error=str(exc))

            try:
                research_results = await self._topic_research(keyword)
                for item in research_results[:5]:
                    topic_name = item.get("topic", "")
                    if topic_name:
                        volume = int(item.get("volume", 0)) if str(item.get("volume", "0")).isdigit() else 0
                        all_topics.append(
                            RawTopic(
                                title=topic_name,
                                description=f"Topic research result for '{keyword}': {topic_name}",
                                engagement_metrics={
                                    "search_volume": volume,
                                    "difficulty": item.get("difficulty", ""),
                                    "efficiency": item.get("efficiency", ""),
                                },
                                source=self.source_name,
                                platform="search",
                                url=f"https://www.google.com/search?q={topic_name}",
                                raw_data=item,
                            )
                        )
            except Exception as exc:
                logger.error("semrush_topic_research_error", topic=keyword, error=str(exc))

        all_topics.sort(
            key=lambda t: t.engagement_metrics.get("search_volume", 0),
            reverse=True,
        )

        logger.info("semrush_scrape_complete", topic_count=len(all_topics))
        return all_topics

    async def health_check(self) -> bool:
        """Check SEMrush API availability."""
        try:
            if not self._api_key:
                return False
            kw_data = await self._keyword_overview("test")
            return bool(kw_data)
        except Exception as exc:
            logger.error("semrush_health_fail", error=str(exc))
            return False
