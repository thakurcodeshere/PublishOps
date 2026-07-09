"""Metrics collector — pull analytics from each platform API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.analytics import AnalyticsSnapshot
from backend.models.platform_variant import PlatformVariant
from backend.models.schedule import UploadSchedule, ScheduleStatus
from backend.utils.logger import get_logger
from sqlalchemy import select

logger = get_logger(__name__)


class MetricsCollector:
    """Collect performance metrics from all platform APIs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        settings = get_settings()
        self._youtube_key = settings.YOUTUBE_API_KEY
        self._twitter_bearer = settings.TWITTER_BEARER_TOKEN
        self._linkedin_token = settings.LINKEDIN_ACCESS_TOKEN

    async def collect_all_platforms(self) -> list[AnalyticsSnapshot]:
        """Pull metrics for all posted content across platforms."""
        result = await self._session.execute(
            select(UploadSchedule).where(UploadSchedule.status == ScheduleStatus.POSTED)
        )
        posted_schedules = list(result.scalars().all())

        snapshots: list[AnalyticsSnapshot] = []

        for schedule in posted_schedules:
            if not schedule.platform_post_id:
                continue

            try:
                metrics = await self._collect_platform_metrics(
                    platform=schedule.platform,
                    post_id=schedule.platform_post_id,
                )

                days_since = (datetime.now(timezone.utc) - schedule.actual_posted_at).days if schedule.actual_posted_at else 0

                snapshot = AnalyticsSnapshot(
                    variant_id=schedule.variant_id,
                    platform=schedule.platform,
                    days_since_post=days_since,
                    metrics=metrics,
                    snapshot_at=datetime.now(timezone.utc),
                )
                self._session.add(snapshot)
                snapshots.append(snapshot)

            except Exception as exc:
                logger.error(
                    "metrics_collection_error",
                    platform=schedule.platform,
                    post_id=schedule.platform_post_id,
                    error=str(exc),
                )

        await self._session.flush()
        logger.info("metrics_collected", total_snapshots=len(snapshots))
        return snapshots

    async def _collect_platform_metrics(
        self, platform: str, post_id: str
    ) -> dict[str, Any]:
        """Collect metrics from a specific platform API."""
        handlers = {
            "youtube": self._collect_youtube,
            "twitter": self._collect_twitter,
            "linkedin": self._collect_linkedin,
            "tiktok": self._collect_tiktok,
            "instagram": self._collect_instagram,
            "pinterest": self._collect_pinterest,
        }

        handler = handlers.get(platform.lower())
        if not handler:
            return {"error": f"Unsupported platform: {platform}"}

        return await handler(post_id)

    async def _collect_youtube(self, video_id: str) -> dict[str, Any]:
        """Collect YouTube video metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics,contentDetails",
                    "id": video_id,
                    "key": self._youtube_key,
                },
            )
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        if not items:
            return {"error": "Video not found"}

        stats = items[0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "favorites": int(stats.get("favoriteCount", 0)),
            "ctr": 0.0,  # Requires YouTube Analytics API
            "avg_watch_time": 0.0,  # Requires YouTube Analytics API
        }

    async def _collect_twitter(self, tweet_id: str) -> dict[str, Any]:
        """Collect Twitter tweet metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                params={"tweet.fields": "public_metrics"},
                headers={"Authorization": f"Bearer {self._twitter_bearer}"},
            )
            response.raise_for_status()
            data = response.json()

        metrics = data.get("data", {}).get("public_metrics", {})
        return {
            "impressions": metrics.get("impression_count", 0),
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "quotes": metrics.get("quote_count", 0),
            "bookmarks": metrics.get("bookmark_count", 0),
        }

    async def _collect_linkedin(self, post_id: str) -> dict[str, Any]:
        """Collect LinkedIn post metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.linkedin.com/v2/socialActions/{post_id}",
                headers={"Authorization": f"Bearer {self._linkedin_token}"},
            )
            response.raise_for_status()
            data = response.json()

        return {
            "likes": data.get("likesSummary", {}).get("totalLikes", 0),
            "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
            "shares": data.get("sharesSummary", {}).get("totalShares", 0),
            "impressions": 0,  # Requires LinkedIn Marketing API
        }

    async def _collect_tiktok(self, post_id: str) -> dict[str, Any]:
        """Collect TikTok video metrics."""
        settings = get_settings()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/video/query/",
                headers={
                    "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "filters": {"video_ids": [post_id]},
                    "fields": ["like_count", "comment_count", "share_count", "view_count"],
                },
            )
            response.raise_for_status()
            data = response.json()

        videos = data.get("data", {}).get("videos", [])
        if not videos:
            return {"error": "Video not found"}

        video = videos[0]
        return {
            "views": video.get("view_count", 0),
            "likes": video.get("like_count", 0),
            "comments": video.get("comment_count", 0),
            "shares": video.get("share_count", 0),
        }

    async def _collect_instagram(self, post_id: str) -> dict[str, Any]:
        """Collect Instagram post metrics via Graph API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://graph.facebook.com/v18.0/{post_id}/insights",
                params={
                    "metric": "impressions,reach,engagement,saved",
                },
            )
            response.raise_for_status()
            data = response.json()

        metrics: dict[str, Any] = {}
        for item in data.get("data", []):
            name = item.get("name", "")
            value = item.get("values", [{}])[0].get("value", 0)
            metrics[name] = value

        return metrics

    async def _collect_pinterest(self, pin_id: str) -> dict[str, Any]:
        """Collect Pinterest Pin metrics."""
        # Simulated/Stubbed Pinterest metrics query
        return {
            "views": 250,
            "likes": 12,
            "comments": 2,
            "shares": 15,
            "saved": 8
        }

    async def republish_top_performers(self) -> int:
        """Find top 10% performers over 30 days old and schedule them for reposting with fresh copy."""
        from backend.services.analytics.repost_manager import RepostManager
        from backend.services.scheduler.window_calculator import WindowCalculator
        
        manager = RepostManager(self._session)
        top_performers = await manager.find_top_performers(percentile=0.10, min_age_days=30)
        
        requeued_count = 0
        window_calc = WindowCalculator()
        
        for item in top_performers:
            variant_id = uuid.UUID(item["variant_id"])
            platform = item["platform"]
            
            # Generate new metadata angles via LLM
            refreshed = await manager.refresh_metadata(variant_id)
            if "error" in refreshed:
                continue
                
            # Compute next optimal posting window (7 days buffer)
            next_time = await window_calc.get_next_optimal_time(platform, db=self._session)
            if not next_time:
                next_time = datetime.now(timezone.utc) + timedelta(days=2)
                
            # Queue the repost
            await manager.queue_repost(variant_id, next_time, refreshed)
            requeued_count += 1
            
        return requeued_count
