"""Intelligence engine — orchestrates all scrapers, deduplicates, and scores."""

from __future__ import annotations

import asyncio
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.intelligence.scorer import ScoredTopic, TopicScorer
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic
from backend.services.intelligence.scrapers.buzzsumo import BuzzSumoScraper
from backend.services.intelligence.scrapers.google_trends import GoogleTrendsScraper
from backend.services.intelligence.scrapers.newsapi import NewsAPIScraper
from backend.services.intelligence.scrapers.pexels import PexelsScraper
from backend.services.intelligence.scrapers.pinterest import PinterestScraper
from backend.services.intelligence.scrapers.reddit import RedditScraper
from backend.services.intelligence.scrapers.semrush import SEMrushScraper
from backend.services.intelligence.scrapers.serpapi import SerpAPIScraper
from backend.services.intelligence.scrapers.tiktok import TikTokScraper
from backend.services.intelligence.scrapers.twitter import TwitterScraper
from backend.services.intelligence.scrapers.youtube import YouTubeScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

DEDUP_THRESHOLD = 0.80


class IntelligenceEngine:
    """Orchestrate all scrapers, deduplicate results, and score topics."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._scrapers: list[BaseScraper] = [
            GoogleTrendsScraper(),
            RedditScraper(),
            YouTubeScraper(),
            TikTokScraper(),
            BuzzSumoScraper(),
            TwitterScraper(),
            NewsAPIScraper(),
            SerpAPIScraper(),
            SEMrushScraper(),
            PexelsScraper(),
            PinterestScraper(),
        ]
        self._scorer = TopicScorer(session=session)

    @property
    def scrapers(self) -> list[BaseScraper]:
        return self._scrapers

    def _titles_similar(self, a: str, b: str) -> bool:
        """Check if two titles are similar using fuzzy matching."""
        ratio = SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()
        return ratio >= DEDUP_THRESHOLD

    def _deduplicate(self, topics: list[RawTopic]) -> list[RawTopic]:
        """Remove near-duplicate topics, merging sources."""
        unique: list[RawTopic] = []
        for topic in topics:
            is_dup = False
            for existing in unique:
                if self._titles_similar(topic.title, existing.title):
                    # Merge source information
                    if topic.source not in (existing.raw_data.get("merged_sources") or []):
                        merged = existing.raw_data.get("merged_sources", [existing.source])
                        merged.append(topic.source)
                        existing.raw_data["merged_sources"] = merged
                    # Keep higher engagement metrics
                    for k, v in topic.engagement_metrics.items():
                        if isinstance(v, (int, float)):
                            current = existing.engagement_metrics.get(k, 0)
                            if isinstance(current, (int, float)) and v > current:
                                existing.engagement_metrics[k] = v
                    is_dup = True
                    break
            if not is_dup:
                unique.append(topic)

        logger.info(
            "deduplication_complete",
            original=len(topics),
            unique=len(unique),
            removed=len(topics) - len(unique),
        )
        return unique

    async def run(
        self,
        active_platforms: list[str] | None = None,
    ) -> list[ScoredTopic]:
        """
        Run all scrapers in parallel, deduplicate, score, and filter.

        Returns a list of ScoredTopics that passed quality thresholds.
        """
        await self._scorer.load_weights_from_db()

        # Run all scrapers concurrently
        tasks = [scraper.scrape() for scraper in self._scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results and log errors
        all_topics: list[RawTopic] = []
        for scraper, result in zip(self._scrapers, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "scraper_failed",
                    scraper=scraper.source_name,
                    error=str(result),
                    error_type=type(result).__name__,
                )
            elif isinstance(result, list):
                logger.info(
                    "scraper_success",
                    scraper=scraper.source_name,
                    topic_count=len(result),
                )
                all_topics.extend(result)

        if not all_topics:
            logger.warning("no_topics_discovered")
            return []

        # Deduplicate
        unique_topics = self._deduplicate(all_topics)

        # Score all topics
        scored: list[ScoredTopic] = []
        for topic in unique_topics:
            scored_topic = self._scorer.score_topic(topic, active_platforms)
            scored.append(scored_topic)

        # Sort by composite score
        scored.sort(key=lambda s: s.composite_score, reverse=True)

        # Filter
        filtered = self._scorer.filter_topics(scored)

        logger.info(
            "intelligence_engine_complete",
            total_scraped=len(all_topics),
            unique=len(unique_topics),
            scored=len(scored),
            passed_filter=len(filtered),
        )

        return filtered

    async def health_check(self) -> dict[str, bool]:
        """Run health checks on all scrapers."""
        results: dict[str, bool] = {}
        tasks = {
            scraper.source_name: scraper.health_check()
            for scraper in self._scrapers
        }

        check_results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        for name, result in zip(tasks.keys(), check_results, strict=False):
            if isinstance(result, Exception):
                results[name] = False
                logger.error("scraper_health_error", scraper=name, error=str(result))
            else:
                results[name] = bool(result)

        return results

    async def close(self) -> None:
        """Close all scraper HTTP clients."""
        for scraper in self._scrapers:
            await scraper.close()
