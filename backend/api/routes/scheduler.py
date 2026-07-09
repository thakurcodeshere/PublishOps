"""Scheduler API routes — upcoming posts, calendar, queue, and windows."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.schedule import ScheduleStatus, UploadSchedule
from backend.services.scheduler.window_calculator import WindowCalculator
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/upcoming", response_model=list[dict])
async def upcoming_posts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the next N scheduled posts ordered by scheduled_at."""
    now = datetime.now(timezone.utc)

    query = (
        select(UploadSchedule)
        .where(
            UploadSchedule.status.in_([ScheduleStatus.SCHEDULED, ScheduleStatus.QUEUED]),
            UploadSchedule.scheduled_at >= now,
        )
        .order_by(UploadSchedule.scheduled_at.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    schedules = list(result.scalars().all())

    return [
        {
            "id": str(s.id),
            "variant_id": str(s.variant_id),
            "platform": s.platform,
            "scheduled_at": s.scheduled_at.isoformat(),
            "jitter_minutes": s.jitter_minutes,
            "status": s.status.value,
            "retry_count": s.retry_count,
            "created_at": s.created_at.isoformat(),
        }
        for s in schedules
    ]


@router.get("/calendar", response_model=dict)
async def calendar_view(
    weeks: int = Query(1, ge=1, le=4, description="Number of weeks to show"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a weekly calendar view of scheduled posts grouped by day."""
    now = datetime.now(timezone.utc)
    # Start from the beginning of today
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_of_today + timedelta(weeks=weeks)

    query = (
        select(UploadSchedule)
        .where(
            UploadSchedule.scheduled_at >= start_of_today,
            UploadSchedule.scheduled_at < end_date,
        )
        .order_by(UploadSchedule.scheduled_at.asc())
    )

    result = await db.execute(query)
    schedules = list(result.scalars().all())

    # Group by date
    calendar: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in schedules:
        day_key = s.scheduled_at.strftime("%Y-%m-%d")
        calendar[day_key].append(
            {
                "id": str(s.id),
                "variant_id": str(s.variant_id),
                "platform": s.platform,
                "scheduled_at": s.scheduled_at.isoformat(),
                "status": s.status.value,
            }
        )

    # Fill empty days
    current = start_of_today
    while current < end_date:
        day_key = current.strftime("%Y-%m-%d")
        if day_key not in calendar:
            calendar[day_key] = []
        current += timedelta(days=1)

    return {
        "start_date": start_of_today.isoformat(),
        "end_date": end_date.isoformat(),
        "days": dict(sorted(calendar.items())),
    }


@router.get("/queue", response_model=dict)
async def queue_status(
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Return queue status counts grouped by status."""
    counts: dict[str, int] = {}

    for status in ScheduleStatus:
        count_result = await db.execute(
            select(func.count(UploadSchedule.id)).where(
                UploadSchedule.status == status
            )
        )
        counts[status.value] = count_result.scalar() or 0

    return counts


@router.post("/reschedule/{schedule_id}", response_model=dict)
async def reschedule_post(
    schedule_id: uuid.UUID,
    new_time: datetime = Body(..., embed=True, description="New scheduled time (UTC)"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update the scheduled_at time for a post."""
    result = await db.execute(
        select(UploadSchedule).where(UploadSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    if schedule.status in (ScheduleStatus.POSTED, ScheduleStatus.UPLOADING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reschedule a post with status '{schedule.status.value}'",
        )

    old_time = schedule.scheduled_at
    schedule.scheduled_at = new_time
    if schedule.status == ScheduleStatus.CANCELLED:
        schedule.status = ScheduleStatus.SCHEDULED
    await db.flush()

    logger.info(
        "post_rescheduled",
        schedule_id=str(schedule_id),
        old_time=old_time.isoformat(),
        new_time=new_time.isoformat(),
    )

    return {
        "schedule_id": str(schedule_id),
        "old_time": old_time.isoformat(),
        "new_time": new_time.isoformat(),
        "status": schedule.status.value,
    }


@router.post("/cancel/{schedule_id}", response_model=dict)
async def cancel_post(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cancel a scheduled post."""
    result = await db.execute(
        select(UploadSchedule).where(UploadSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    if schedule.status == ScheduleStatus.POSTED:
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel an already-posted entry",
        )

    if schedule.status == ScheduleStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Post is already cancelled")

    schedule.status = ScheduleStatus.CANCELLED
    await db.flush()

    logger.info("post_cancelled", schedule_id=str(schedule_id), platform=schedule.platform)

    return {
        "schedule_id": str(schedule_id),
        "status": schedule.status.value,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/windows", response_model=dict)
async def posting_windows(
    platform: str | None = Query(None, description="Filter by platform"),
    days_ahead: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return optimal posting windows per platform."""
    calculator = WindowCalculator()
    platforms = [platform.lower()] if platform else [
        "youtube", "tiktok", "instagram", "twitter", "linkedin"
    ]

    # Gather existing scheduled times to avoid conflicts
    scheduled_result = await db.execute(
        select(UploadSchedule.scheduled_at).where(
            UploadSchedule.status.in_([ScheduleStatus.SCHEDULED, ScheduleStatus.QUEUED])
        )
    )
    existing_posts = [row[0] for row in scheduled_result.all()]

    windows: dict[str, list[dict[str, Any]]] = {}
    for p in platforms:
        platform_windows = calculator.calculate_optimal_windows(
            platform=p,
            existing_posts=existing_posts,
            days_ahead=days_ahead,
        )
        windows[p] = [
            {
                "start": w.start.isoformat(),
                "end": w.end.isoformat(),
                "weight": w.weight,
                "reason": w.reason,
            }
            for w in platform_windows[:10]  # Top 10 windows per platform
        ]

    return {"windows": windows, "days_ahead": days_ahead}


@router.post("/recalculate-windows", response_model=dict)
async def recalculate_windows(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Recalculate posting windows from audience data (called by Airflow)."""
    calculator = WindowCalculator()
    platforms = ["youtube", "tiktok", "instagram", "twitter", "linkedin"]

    # Gather existing scheduled times
    scheduled_result = await db.execute(
        select(UploadSchedule.scheduled_at).where(
            UploadSchedule.status.in_([ScheduleStatus.SCHEDULED, ScheduleStatus.QUEUED])
        )
    )
    existing_posts = [row[0] for row in scheduled_result.all()]

    results: dict[str, int] = {}
    for p in platforms:
        windows = calculator.calculate_optimal_windows(
            platform=p,
            existing_posts=existing_posts,
            days_ahead=14,
        )
        results[p] = len(windows)

    logger.info("windows_recalculated", results=results)
    return {
        "status": "completed",
        "windows_per_platform": results,
        "recalculated_at": datetime.now(timezone.utc).isoformat(),
    }
