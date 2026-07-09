"""Topics API routes — discover, list, filter, accept/reject trending topics."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.topic import Topic, TopicStatus
from backend.schemas.topic import TopicList, TopicResponse
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=TopicList)
async def list_topics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    status: str | None = Query(None, description="Filter by topic status"),
    sort_by: str = Query("composite_score", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
) -> TopicList:
    """List topics with pagination, optional status filter, sorted by composite_score."""
    query = select(Topic)

    if status is not None:
        try:
            status_enum = TopicStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {[s.value for s in TopicStatus]}",
            )
        query = query.where(Topic.status == status_enum)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Topic, sort_by, Topic.composite_score)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    topics = list(result.scalars().all())

    page = (skip // limit) + 1 if limit > 0 else 1
    pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1

    return TopicList(
        items=[TopicResponse.model_validate(t) for t in topics],
        total=total,
        page=page,
        page_size=limit,
        pages=pages,
    )


@router.get("/trending", response_model=list[TopicResponse])
async def trending_topics(
    min_score: float = Query(65.0, ge=0, le=100, description="Minimum composite score"),
    hours: int = Query(24, ge=1, le=168, description="Look-back window in hours"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    db: AsyncSession = Depends(get_db),
) -> list[TopicResponse]:
    """Return latest discovered topics from the last N hours above a score threshold."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = (
        select(Topic)
        .where(
            Topic.discovered_at >= cutoff,
            Topic.composite_score >= min_score,
        )
        .order_by(Topic.composite_score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    topics = list(result.scalars().all())

    logger.info(
        "trending_topics_fetched",
        count=len(topics),
        min_score=min_score,
        hours=hours,
    )
    return [TopicResponse.model_validate(t) for t in topics]


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """Get a single topic with full score breakdown."""
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()

    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    return TopicResponse.model_validate(topic)


@router.post("/{topic_id}/accept", response_model=TopicResponse)
async def accept_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """Accept a topic for content production."""
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()

    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    if topic.status == TopicStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Topic is already accepted")

    topic.status = TopicStatus.ACCEPTED
    await db.flush()

    logger.info("topic_accepted", topic_id=str(topic_id), title=topic.title)
    return TopicResponse.model_validate(topic)


@router.post("/{topic_id}/reject", response_model=TopicResponse)
async def reject_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """Reject a topic from content production."""
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()

    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    if topic.status == TopicStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Topic is already rejected")

    topic.status = TopicStatus.REJECTED
    await db.flush()

    logger.info("topic_rejected", topic_id=str(topic_id), title=topic.title)
    return TopicResponse.model_validate(topic)
