"""Repost manager — find top performers, refresh metadata, and re-queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.analytics import AnalyticsSnapshot
from backend.models.platform_variant import PlatformVariant
from backend.models.schedule import ScheduleStatus, UploadSchedule
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RepostManager:
    """Identify top-performing content for re-posting with refreshed metadata."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        settings = get_settings()
        self._claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def find_top_performers(
        self,
        percentile: float = 0.10,
        min_age_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Find top-performing content (top 10% by engagement, older than 30 days).
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=min_age_days)

        # Get all snapshots for older content
        result = await self._session.execute(
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.snapshot_at <= cutoff_date)
        )
        snapshots = list(result.scalars().all())

        if not snapshots:
            return []

        # Calculate total engagement per variant
        variant_engagement: dict[uuid.UUID, float] = {}
        for snap in snapshots:
            vid = snap.variant_id
            if isinstance(snap.metrics, dict):
                engagement = (
                    snap.metrics.get("views", 0) * 0.1
                    + snap.metrics.get("likes", 0) * 1
                    + snap.metrics.get("comments", 0) * 3
                    + snap.metrics.get("shares", 0) * 5
                    + snap.metrics.get("saved", 0) * 4
                )
                variant_engagement[vid] = variant_engagement.get(vid, 0) + engagement

        if not variant_engagement:
            return []

        # Sort and get top percentile
        sorted_variants = sorted(
            variant_engagement.items(), key=lambda x: x[1], reverse=True
        )
        top_count = max(1, int(len(sorted_variants) * percentile))
        top_variants = sorted_variants[:top_count]

        # Load variant details
        results: list[dict[str, Any]] = []
        for variant_id, engagement_score in top_variants:
            variant_result = await self._session.execute(
                select(PlatformVariant).where(PlatformVariant.id == variant_id)
            )
            variant = variant_result.scalar_one_or_none()
            if variant:
                results.append({
                    "variant_id": str(variant.id),
                    "platform": variant.platform,
                    "title": variant.title,
                    "engagement_score": round(engagement_score, 2),
                    "s3_key": variant.s3_key,
                })

        logger.info(
            "top_performers_found",
            total_variants=len(variant_engagement),
            top_count=len(results),
            percentile=percentile,
        )
        return results

    async def refresh_metadata(
        self,
        variant_id: uuid.UUID,
    ) -> dict[str, str]:
        """
        Generate refreshed title, description, and thumbnail text for a repost.
        """
        result = await self._session.execute(
            select(PlatformVariant).where(PlatformVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            return {"error": "Variant not found"}

        try:
            response = await self._claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Refresh this content's metadata for a repost on {variant.platform}.
Original title: {variant.title}
Original caption excerpt: {(variant.caption or '')[:200]}

Generate a fresh:
1. Title (different angle, same topic)
2. Description/caption (new hook, updated framing)
3. Thumbnail text (3-5 words for overlay)

Output as JSON with keys: title, description, thumbnail_text""",
                    }
                ],
            )

            import json
            text = response.content[0].text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            refreshed = json.loads(text)

            logger.info("metadata_refreshed", variant_id=str(variant_id))
            return refreshed

        except Exception as exc:
            logger.error("metadata_refresh_error", error=str(exc))
            return {
                "title": f"[UPDATED] {variant.title}",
                "description": variant.caption or "",
                "thumbnail_text": "NEW PERSPECTIVE",
            }

    async def queue_repost(
        self,
        variant_id: uuid.UUID,
        scheduled_at: datetime,
        refreshed_metadata: dict[str, str] | None = None,
    ) -> UploadSchedule:
        """Queue a repost in the upload schedule."""
        result = await self._session.execute(
            select(PlatformVariant).where(PlatformVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            raise ValueError(f"Variant {variant_id} not found")

        # Update variant metadata if provided
        if refreshed_metadata:
            if refreshed_metadata.get("title"):
                variant.title = refreshed_metadata["title"]
            if refreshed_metadata.get("description"):
                variant.caption = refreshed_metadata["description"]

        schedule = UploadSchedule(
            variant_id=variant_id,
            platform=variant.platform,
            scheduled_at=scheduled_at,
            status=ScheduleStatus.SCHEDULED,
        )
        self._session.add(schedule)
        await self._session.flush()

        logger.info(
            "repost_queued",
            variant_id=str(variant_id),
            platform=variant.platform,
            scheduled_at=scheduled_at.isoformat(),
        )
        return schedule
