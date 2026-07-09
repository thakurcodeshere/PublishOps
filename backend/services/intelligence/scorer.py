"""Topic scorer — composite scoring with configurable weights."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.analytics import ScoringWeight
from backend.services.intelligence.scrapers.base import RawTopic
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScoredTopic:
    """A topic with all computed scores."""

    raw: RawTopic
    composite_score: float = 0.0
    velocity_score: float = 0.0
    evergreen_score: float = 0.0
    platform_fit: float = 0.0
    saturation: float = 0.0
    active_platforms: list[str] = field(default_factory=list)


class TopicScorer:
    """Score topics using a weighted multi-signal model."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        settings = get_settings()
        self._velocity_weight = settings.VELOCITY_WEIGHT
        self._evergreen_weight = settings.EVERGREEN_WEIGHT
        self._fit_weight = settings.FIT_WEIGHT
        self._saturation_weight = settings.SATURATION_WEIGHT
        self._min_score = settings.MIN_SCORE_THRESHOLD
        self._max_saturation = settings.MAX_SATURATION

    async def load_weights_from_db(self) -> None:
        """Load latest scoring weights from the database."""
        if self._session is None:
            return
        try:
            result = await self._session.execute(
                select(ScoringWeight).order_by(ScoringWeight.iteration.desc()).limit(1)
            )
            weight_row = result.scalar_one_or_none()
            if weight_row:
                self._velocity_weight = weight_row.velocity_weight
                self._evergreen_weight = weight_row.evergreen_weight
                self._fit_weight = weight_row.fit_weight
                self._saturation_weight = weight_row.saturation_weight
                logger.info(
                    "scoring_weights_loaded",
                    iteration=weight_row.iteration,
                    velocity=self._velocity_weight,
                    evergreen=self._evergreen_weight,
                    fit=self._fit_weight,
                    saturation=self._saturation_weight,
                )
        except Exception as exc:
            logger.warning("scoring_weights_db_error", error=str(exc))

    def calculate_velocity_score(self, topic: RawTopic) -> float:
        """
        Calculate velocity score (0-100) from engagement metrics.

        Considers: views/time, engagement rate, social shares velocity.
        """
        metrics = topic.engagement_metrics
        signals: list[float] = []

        # Comment/engagement velocity
        comment_vel = metrics.get("comment_velocity", 0)
        if comment_vel > 0:
            signals.append(min(100, math.log1p(comment_vel) * 20))

        # View/engagement counts (normalised)
        view_count = metrics.get("view_count", 0) or metrics.get("total_views", 0)
        if view_count > 0:
            signals.append(min(100, math.log10(max(view_count, 1)) * 15))

        # Social shares velocity
        content_vel = metrics.get("content_velocity", 0)
        if content_vel > 0:
            signals.append(min(100, math.log1p(content_vel) * 25))

        # Tweet volume
        tweet_vol = metrics.get("tweet_volume", 0)
        if tweet_vol > 0:
            signals.append(min(100, math.log10(max(tweet_vol, 1)) * 18))

        # Engagement velocity (YouTube)
        eng_vel = metrics.get("engagement_velocity", 0)
        if eng_vel > 0:
            signals.append(min(100, eng_vel))

        # Search volume (SEMrush)
        search_vol = metrics.get("search_volume", 0)
        if search_vol > 0:
            signals.append(min(100, math.log10(max(search_vol, 1)) * 20))

        # Reddit score
        reddit_score = metrics.get("score", 0)
        if reddit_score > 0:
            signals.append(min(100, math.log10(max(reddit_score, 1)) * 20))

        # Trending rank (lower = better)
        trending_rank = metrics.get("trending_rank", 0)
        if trending_rank > 0:
            signals.append(max(0, 100 - trending_rank * 3))

        if not signals:
            return 25.0  # Default baseline for topics with no velocity data

        return round(sum(signals) / len(signals), 1)

    def calculate_evergreen_score(self, topic: RawTopic) -> float:
        """
        Calculate evergreen score (0-100).

        Higher for topics that stay relevant longer.
        Educational, how-to, and explainer topics score higher.
        Breaking news and event-specific topics score lower.
        """
        title_lower = topic.title.lower()
        desc_lower = topic.description.lower()
        combined = f"{title_lower} {desc_lower}"

        score = 50.0  # Base score

        # Evergreen indicators (boost)
        evergreen_signals = [
            "how to", "guide", "tutorial", "explained", "what is",
            "best practices", "tips", "fundamentals", "101",
            "beginner", "complete guide", "ultimate",
        ]
        for signal in evergreen_signals:
            if signal in combined:
                score += 10

        # Ephemeral indicators (reduce)
        ephemeral_signals = [
            "breaking", "just in", "today", "tonight", "this week",
            "2024", "2025", "2026", "election", "game", "match",
            "season finale", "premiere", "controversy",
        ]
        for signal in ephemeral_signals:
            if signal in combined:
                score -= 8

        # BuzzSumo evergreen score if available
        buzzsumo_eg = topic.engagement_metrics.get("evergreen_score", 0)
        if buzzsumo_eg > 0:
            score = (score + buzzsumo_eg) / 2

        return round(max(0, min(100, score)), 1)

    def calculate_platform_fit(
        self,
        topic: RawTopic,
        active_platforms: list[str] | None = None,
    ) -> float:
        """
        Calculate platform fit (0-100).

        Considers source platform alignment and content format potential.
        """
        platforms = active_platforms or [
            "youtube", "tiktok", "instagram", "twitter", "linkedin"
        ]
        source = topic.platform.lower()
        title_lower = topic.title.lower()

        fit_scores: list[float] = []

        platform_scoring: dict[str, float] = {
            "youtube": 70.0,
            "tiktok": 70.0,
            "instagram": 60.0,
            "twitter": 65.0,
            "linkedin": 55.0,
        }

        for platform in platforms:
            base = platform_scoring.get(platform, 50.0)

            # Boost if source matches target platform
            if source == platform:
                base += 15

            # Visual content boost for visual platforms
            if platform in ("tiktok", "instagram", "youtube"):
                if topic.engagement_metrics.get("source_type") in (
                    "curated_photo", "popular_video"
                ):
                    base += 10

            # Text-heavy content boost for text platforms
            if platform in ("twitter", "linkedin"):
                word_count = topic.raw_data.get("word_count", 0)
                if isinstance(word_count, int) and word_count > 500:
                    base += 10

            # Professional topic boost for LinkedIn
            if platform == "linkedin":
                professional_signals = [
                    "business", "career", "leadership", "management",
                    "startup", "enterprise", "industry",
                ]
                if any(s in title_lower for s in professional_signals):
                    base += 15

            fit_scores.append(min(100, base))

        return round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else 50.0

    def calculate_saturation(self, topic: RawTopic) -> float:
        """
        Calculate market saturation (0-1).

        Higher values = more competition = harder to stand out.
        """
        metrics = topic.engagement_metrics

        # Number of Google results as saturation proxy
        num_results = metrics.get("num_results", 0)
        competition = metrics.get("competition", 0)

        saturation = 0.3  # Default moderate saturation

        if num_results > 0:
            # Log scale: 1M results ≈ 0.6, 100M ≈ 0.8, 1B ≈ 1.0
            saturation = min(1.0, math.log10(max(num_results, 1)) / 10)

        if competition > 0:
            # SEMrush competition score (0-1)
            saturation = (saturation + float(competition)) / 2

        # High share count implies more coverage
        total_shares = metrics.get("total_shares", 0)
        if total_shares > 10000:
            saturation = min(1.0, saturation + 0.1)

        return round(saturation, 3)

    def score_topic(
        self,
        topic: RawTopic,
        active_platforms: list[str] | None = None,
    ) -> ScoredTopic:
        """Calculate all scores and composite for a single topic."""
        platforms = active_platforms or [
            "youtube", "tiktok", "instagram", "twitter", "linkedin"
        ]

        velocity = self.calculate_velocity_score(topic)
        evergreen = self.calculate_evergreen_score(topic)
        fit = self.calculate_platform_fit(topic, platforms)
        saturation = self.calculate_saturation(topic)

        # Composite: weighted sum, with saturation as a penalty
        composite = (
            velocity * self._velocity_weight
            + evergreen * self._evergreen_weight
            + fit * self._fit_weight
            - (saturation * 100) * self._saturation_weight
        )
        composite = round(max(0, min(100, composite)), 1)

        return ScoredTopic(
            raw=topic,
            composite_score=composite,
            velocity_score=velocity,
            evergreen_score=evergreen,
            platform_fit=fit,
            saturation=saturation,
            active_platforms=platforms,
        )

    def filter_topics(self, scored_topics: list[ScoredTopic]) -> list[ScoredTopic]:
        """Filter out topics below threshold or above saturation limit."""
        filtered: list[ScoredTopic] = []
        for st in scored_topics:
            if st.composite_score < self._min_score:
                logger.debug(
                    "topic_filtered_low_score",
                    title=st.raw.title,
                    score=st.composite_score,
                )
                continue
            if st.saturation > self._max_saturation:
                logger.debug(
                    "topic_filtered_high_saturation",
                    title=st.raw.title,
                    saturation=st.saturation,
                )
                continue
            filtered.append(st)

        logger.info(
            "topics_filtered",
            total=len(scored_topics),
            passed=len(filtered),
            rejected=len(scored_topics) - len(filtered),
        )
        return filtered
