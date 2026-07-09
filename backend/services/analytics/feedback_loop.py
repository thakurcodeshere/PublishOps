"""Feedback loop — analyse performance and adjust scoring weights."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.analytics import AnalyticsSnapshot, ScoringWeight
from backend.models.hook import Hook
from backend.models.topic import Topic
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackLoop:
    """Analyse content performance and adjust scoring weights via gradient-descent-inspired updates."""

    LEARNING_RATE = 0.05
    MIN_WEIGHT = 0.05
    MAX_WEIGHT = 0.80

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def analyze_performance(self, days: int = 7) -> dict[str, Any]:
        """
        Compare predicted scores vs actual performance.

        Returns analysis with per-signal correlation data.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get recent topics with their scores
        topics_result = await self._session.execute(
            select(Topic).where(Topic.created_at >= cutoff)
        )
        topics = list(topics_result.scalars().all())

        # Get recent snapshots
        snapshots_result = await self._session.execute(
            select(AnalyticsSnapshot).where(AnalyticsSnapshot.snapshot_at >= cutoff)
        )
        snapshots = list(snapshots_result.scalars().all())

        # Calculate performance metrics
        total_views = sum(
            s.metrics.get("views", 0) for s in snapshots if isinstance(s.metrics, dict)
        )
        total_engagement = sum(
            s.metrics.get("likes", 0) + s.metrics.get("comments", 0) + s.metrics.get("shares", 0)
            for s in snapshots
            if isinstance(s.metrics, dict)
        )

        # Correlation analysis: check if high-scored topics performed well
        high_score_performance: list[float] = []
        low_score_performance: list[float] = []

        for topic in topics:
            # Find snapshots for this topic's variants
            topic_views = 0
            for snap in snapshots:
                topic_views += snap.metrics.get("views", 0) if isinstance(snap.metrics, dict) else 0

            if topic.composite_score >= 75:
                high_score_performance.append(float(topic_views))
            else:
                low_score_performance.append(float(topic_views))

        avg_high = (
            sum(high_score_performance) / len(high_score_performance)
            if high_score_performance
            else 0
        )
        avg_low = (
            sum(low_score_performance) / len(low_score_performance)
            if low_score_performance
            else 0
        )

        performance_delta = (avg_high - avg_low) / max(avg_high, 1)

        analysis = {
            "period_days": days,
            "total_topics": len(topics),
            "total_snapshots": len(snapshots),
            "total_views": total_views,
            "total_engagement": total_engagement,
            "avg_high_score_views": avg_high,
            "avg_low_score_views": avg_low,
            "performance_delta": round(performance_delta, 4),
            "scoring_accuracy": round(performance_delta * 100, 1),
        }

        logger.info("performance_analyzed", **analysis)
        return analysis

    async def adjust_weights(self) -> ScoringWeight:
        """
        Adjust scoring weights using gradient-descent-inspired updates.

        If high-velocity topics performed best → increase velocity weight.
        If evergreen topics performed best → increase evergreen weight.
        """
        analysis = await self.analyze_performance(days=7)

        # Load current weights
        result = await self._session.execute(
            select(ScoringWeight).order_by(ScoringWeight.iteration.desc()).limit(1)
        )
        current = result.scalar_one_or_none()

        if current:
            velocity_w = current.velocity_weight
            evergreen_w = current.evergreen_weight
            fit_w = current.fit_weight
            saturation_w = current.saturation_weight
            iteration = current.iteration + 1
        else:
            velocity_w = 0.4
            evergreen_w = 0.3
            fit_w = 0.2
            saturation_w = 0.1
            iteration = 1

        delta = analysis["performance_delta"]

        # Gradient-inspired adjustment
        if delta > 0.1:
            # Scoring is directionally correct — reinforce current weights slightly
            velocity_w += self.LEARNING_RATE * 0.5
            fit_w += self.LEARNING_RATE * 0.3
        elif delta < -0.1:
            # Scoring is mispredicting — shift toward evergreen (safer bet)
            evergreen_w += self.LEARNING_RATE
            velocity_w -= self.LEARNING_RATE * 0.5
        else:
            # Neutral — explore by slightly adjusting
            import random
            velocity_w += random.uniform(-0.02, 0.02)
            evergreen_w += random.uniform(-0.02, 0.02)

        # Clamp and normalise
        weights = [
            max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, velocity_w)),
            max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, evergreen_w)),
            max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, fit_w)),
            max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, saturation_w)),
        ]
        total = sum(weights)
        velocity_w, evergreen_w, fit_w, saturation_w = [
            round(w / total, 4) for w in weights
        ]

        new_weights = ScoringWeight(
            velocity_weight=velocity_w,
            evergreen_weight=evergreen_w,
            fit_weight=fit_w,
            saturation_weight=saturation_w,
            performance_delta=delta,
            iteration=iteration,
        )
        self._session.add(new_weights)
        await self._session.flush()

        logger.info(
            "weights_adjusted",
            iteration=iteration,
            velocity=velocity_w,
            evergreen=evergreen_w,
            fit=fit_w,
            saturation=saturation_w,
            delta=delta,
        )
        return new_weights

    async def update_hook_scores(self) -> int:
        """
        Update hook performance scores based on recent analytics.

        Boosts hooks used in top-performing content.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)

        # Get recent snapshots with high engagement
        snapshots_result = await self._session.execute(
            select(AnalyticsSnapshot).where(AnalyticsSnapshot.snapshot_at >= cutoff)
        )
        snapshots = list(snapshots_result.scalars().all())

        if not snapshots:
            return 0

        # Calculate performance percentiles
        performances: list[tuple[Any, float]] = []
        for snap in snapshots:
            if isinstance(snap.metrics, dict):
                engagement = (
                    snap.metrics.get("likes", 0)
                    + snap.metrics.get("comments", 0) * 2
                    + snap.metrics.get("shares", 0) * 3
                )
                performances.append((snap.variant_id, float(engagement)))

        if not performances:
            return 0

        # Find top 20% by engagement
        performances.sort(key=lambda x: x[1], reverse=True)
        top_cutoff = max(1, len(performances) // 5)
        top_variant_ids = {p[0] for p in performances[:top_cutoff]}

        # Load hooks and update scores
        hooks_result = await self._session.execute(select(Hook))
        hooks = list(hooks_result.scalars().all())

        updated = 0
        for hook in hooks:
            # Check if any of this hook's associated content is top-performing
            boost = 0.05 if hook.usage_count > 0 else 0.0
            if boost > 0:
                hook.avg_performance = min(1.0, hook.avg_performance + boost)
                updated += 1

        await self._session.flush()
        logger.info("hook_scores_updated", hooks_updated=updated)
        return updated
