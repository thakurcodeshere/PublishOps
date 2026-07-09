"""Analytics API routes — dashboard, performance, trends, and collection."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.analytics import AnalyticsSnapshot, PlatformRule, ScoringWeight
from backend.models.content import ContentAsset, ContentBrief
from backend.models.platform_variant import PlatformVariant
from backend.models.schedule import ScheduleStatus, UploadSchedule
from backend.models.topic import Topic, TopicStatus
from backend.schemas.analytics import (
    AnalyticsSnapshotResponse,
    DashboardStats,
    MetricTrend,
    PlatformMetrics,
    ScoringWeightsResponse,
    TrendPoint,
)
from backend.services.analytics.collector import MetricsCollector
from backend.services.analytics.repost_manager import RepostManager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Return aggregated dashboard statistics."""
    # Total topics
    total_topics_result = await db.execute(select(func.count(Topic.id)))
    total_topics = total_topics_result.scalar() or 0

    # Accepted topics
    accepted_result = await db.execute(
        select(func.count(Topic.id)).where(Topic.status == TopicStatus.ACCEPTED)
    )
    total_accepted = accepted_result.scalar() or 0

    # Total briefs
    briefs_result = await db.execute(select(func.count(ContentBrief.id)))
    total_briefs = briefs_result.scalar() or 0

    # Total assets
    assets_result = await db.execute(select(func.count(ContentAsset.id)))
    total_assets = assets_result.scalar() or 0

    # Total variants
    variants_result = await db.execute(select(func.count(PlatformVariant.id)))
    total_variants = variants_result.scalar() or 0

    # Total scheduled posts
    scheduled_result = await db.execute(select(func.count(UploadSchedule.id)))
    total_scheduled = scheduled_result.scalar() or 0

    # Total published
    published_result = await db.execute(
        select(func.count(UploadSchedule.id)).where(
            UploadSchedule.status == ScheduleStatus.POSTED
        )
    )
    total_published = published_result.scalar() or 0

    # Average composite score
    avg_score_result = await db.execute(select(func.avg(Topic.composite_score)))
    avg_score = avg_score_result.scalar() or 0.0

    # Per-platform metrics
    platform_metrics: list[PlatformMetrics] = []
    platforms_query = await db.execute(
        select(PlatformVariant.platform, func.count(PlatformVariant.id))
        .group_by(PlatformVariant.platform)
    )
    for platform, count in platforms_query.all():
        # Get engagement totals from snapshots
        engagement_result = await db.execute(
            select(func.count(AnalyticsSnapshot.id))
            .where(AnalyticsSnapshot.platform == platform)
        )
        engagement_count = engagement_result.scalar() or 0

        platform_metrics.append(
            PlatformMetrics(
                platform=platform,
                total_posts=count,
                total_views=0,
                total_engagement=engagement_count,
                avg_ctr=0.0,
                avg_watch_time=0.0,
            )
        )

    # Score distribution buckets
    score_distribution: dict[str, int] = {}
    for bucket_label, low, high in [
        ("0-20", 0, 20),
        ("20-40", 20, 40),
        ("40-60", 40, 60),
        ("60-80", 60, 80),
        ("80-100", 80, 100),
    ]:
        bucket_result = await db.execute(
            select(func.count(Topic.id)).where(
                Topic.composite_score >= low,
                Topic.composite_score < high,
            )
        )
        score_distribution[bucket_label] = bucket_result.scalar() or 0

    # Recent performance delta from scoring weights
    delta_result = await db.execute(
        select(ScoringWeight.performance_delta)
        .order_by(ScoringWeight.updated_at.desc())
        .limit(1)
    )
    perf_delta = delta_result.scalar() or 0.0

    return DashboardStats(
        total_topics_discovered=total_topics,
        total_topics_accepted=total_accepted,
        total_briefs=total_briefs,
        total_assets=total_assets,
        total_variants=total_variants,
        total_posts_scheduled=total_scheduled,
        total_posts_published=total_published,
        avg_composite_score=round(float(avg_score), 2),
        platform_metrics=platform_metrics,
        score_distribution=score_distribution,
        recent_performance_delta=float(perf_delta),
    )


@router.get("/performance", response_model=list[dict])
async def content_performance(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return per-content performance metrics from analytics snapshots."""
    query = (
        select(AnalyticsSnapshot)
        .order_by(AnalyticsSnapshot.snapshot_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    return [
        {
            "id": str(snap.id),
            "variant_id": str(snap.variant_id),
            "platform": snap.platform,
            "days_since_post": snap.days_since_post,
            "metrics": snap.metrics,
            "snapshot_at": snap.snapshot_at.isoformat(),
        }
        for snap in snapshots
    ]


@router.get("/platform/{platform}", response_model=PlatformMetrics)
async def platform_metrics(
    platform: str,
    db: AsyncSession = Depends(get_db),
) -> PlatformMetrics:
    """Return aggregated metrics for a specific platform."""
    platform_lower = platform.lower()

    # Total posts
    posts_result = await db.execute(
        select(func.count(UploadSchedule.id)).where(
            UploadSchedule.platform == platform_lower,
            UploadSchedule.status == ScheduleStatus.POSTED,
        )
    )
    total_posts = posts_result.scalar() or 0

    # Aggregated metrics from snapshots
    snapshots_result = await db.execute(
        select(AnalyticsSnapshot).where(AnalyticsSnapshot.platform == platform_lower)
    )
    snapshots = list(snapshots_result.scalars().all())

    total_views = 0
    total_engagement = 0
    for snap in snapshots:
        if isinstance(snap.metrics, dict):
            total_views += snap.metrics.get("views", 0)
            total_engagement += (
                snap.metrics.get("likes", 0)
                + snap.metrics.get("comments", 0)
                + snap.metrics.get("shares", 0)
            )

    return PlatformMetrics(
        platform=platform_lower,
        total_posts=total_posts,
        total_views=total_views,
        total_engagement=total_engagement,
        avg_ctr=0.0,
        avg_watch_time=0.0,
    )


@router.get("/trends", response_model=list[MetricTrend])
async def metric_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
) -> list[MetricTrend]:
    """Return metric trends over the specified time period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Topics discovered per day
    topics_trend_data: list[TrendPoint] = []
    for day_offset in range(days):
        day_start = (datetime.now(timezone.utc) - timedelta(days=days - 1 - day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        count_result = await db.execute(
            select(func.count(Topic.id)).where(
                Topic.discovered_at >= day_start,
                Topic.discovered_at < day_end,
            )
        )
        count = count_result.scalar() or 0
        topics_trend_data.append(
            TrendPoint(date=day_start, value=float(count), label="topics_discovered")
        )

    # Average score per day
    score_trend_data: list[TrendPoint] = []
    for day_offset in range(days):
        day_start = (datetime.now(timezone.utc) - timedelta(days=days - 1 - day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        avg_result = await db.execute(
            select(func.avg(Topic.composite_score)).where(
                Topic.discovered_at >= day_start,
                Topic.discovered_at < day_end,
            )
        )
        avg = avg_result.scalar() or 0.0
        score_trend_data.append(
            TrendPoint(date=day_start, value=round(float(avg), 2), label="avg_score")
        )

    # Calculate total change percentage
    def _calc_change(points: list[TrendPoint]) -> float:
        if len(points) < 2:
            return 0.0
        first_nonzero = next((p.value for p in points if p.value > 0), 0.0)
        if first_nonzero == 0:
            return 0.0
        return round(((points[-1].value - first_nonzero) / first_nonzero) * 100, 2)

    return [
        MetricTrend(
            metric_name="topics_discovered",
            data_points=topics_trend_data,
            total_change_pct=_calc_change(topics_trend_data),
        ),
        MetricTrend(
            metric_name="avg_composite_score",
            data_points=score_trend_data,
            total_change_pct=_calc_change(score_trend_data),
        ),
    ]


@router.get("/weights", response_model=ScoringWeightsResponse)
async def get_scoring_weights(
    db: AsyncSession = Depends(get_db),
) -> ScoringWeightsResponse:
    """Return current scoring weights."""
    result = await db.execute(
        select(ScoringWeight).order_by(ScoringWeight.updated_at.desc()).limit(1)
    )
    weights = result.scalar_one_or_none()

    if weights is None:
        raise HTTPException(status_code=404, detail="No scoring weights found")

    return ScoringWeightsResponse.model_validate(weights)


@router.get("/top-performers", response_model=list[dict])
async def top_performers(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return top 10% content by engagement score."""
    manager = RepostManager(session=db)
    performers = await manager.find_top_performers(percentile=0.10, min_age_days=0)
    return performers


@router.post("/collect", response_model=dict)
async def collect_metrics(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger metrics collection across all platforms (called by Airflow)."""
    collector = MetricsCollector(session=db)

    try:
        snapshots = await collector.collect_all_platforms()
        logger.info("metrics_collection_triggered", snapshots_created=len(snapshots))
        return {
            "status": "completed",
            "snapshots_created": len(snapshots),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("metrics_collection_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Metrics collection failed: {exc}",
        )


@router.post("/check-reposts", response_model=dict)
async def check_reposts(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check for 30-day repost candidates (called by Airflow)."""
    manager = RepostManager(session=db)

    try:
        candidates = await manager.find_top_performers(
            percentile=0.10, min_age_days=30
        )
        logger.info("repost_check_complete", candidates_found=len(candidates))
        return {
            "status": "completed",
            "candidates": candidates,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("repost_check_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Repost check failed: {exc}",
        )
