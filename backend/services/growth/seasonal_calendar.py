"""Seasonal Calendar service (Tier E) for preloading recurring milestones and early campaign scheduling."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import ContentBrief, BriefStatus
from backend.models.seasonal_event import EventContentPlan, SeasonalEvent
from backend.models.topic import Topic, TopicStatus

logger = logging.getLogger(__name__)


class SeasonalCalendar:
    """Tracks annual events and schedules campaigns 3-4 weeks before search volume peaks."""

    async def seed_events(self, db: AsyncSession, seed_file_path: str = "") -> int:
        """Seed the seasonal events database from JSON seed file or static fallback."""
        events_to_seed = []
        
        # Load from seed file if exists
        if seed_file_path and os.path.exists(seed_file_path):
            try:
                with open(seed_file_path, "r", encoding="utf-8") as f:
                    events_to_seed = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load seed file {seed_file_path}: {e}")

        # Fallback default seed list
        if not events_to_seed:
            now = datetime.now(timezone.utc)
            events_to_seed = [
                {
                    "name": "AWS re:Invent Conference",
                    "niche": "technology",
                    "month": 11,
                    "day": 28,
                    "description": "Annual Amazon Web Services conference detailing next-gen cloud launches."
                },
                {
                    "name": "Apple WWDC Developers Keynote",
                    "niche": "technology",
                    "month": 6,
                    "day": 5,
                    "description": "Apple Worldwide Developers Conference revealing macOS, iOS, and AI SDK updates."
                },
                {
                    "name": "GitHub Universe",
                    "niche": "technology",
                    "month": 10,
                    "day": 25,
                    "description": "GitHub's global community event launching new developer productivity features."
                },
                {
                    "name": "Black Friday Sales Pitch",
                    "niche": "sales",
                    "month": 11,
                    "day": 27,
                    "description": "Major retail and digital course sales event requiring promotion offers."
                },
                {
                    "name": "New Year Solopreneur Planning",
                    "niche": "general",
                    "month": 1,
                    "day": 1,
                    "description": "Goal-setting and workflow restructuring content for independent creators."
                }
            ]

        seeded_count = 0
        now = datetime.now(timezone.utc)
        
        for item in events_to_seed:
            # Check if event already exists by name
            check = await db.execute(select(SeasonalEvent).where(SeasonalEvent.name == item["name"]))
            if not check.scalar_one_or_none():
                # Project event date to the current or next year
                event_year = now.year
                # If month/day already passed this year, schedule for next year
                if item.get("month", 1) < now.month or (item.get("month", 1) == now.month and item.get("day", 1) < now.day):
                    event_year += 1
                    
                event_date = datetime(
                    year=event_year,
                    month=item.get("month", 1),
                    day=item.get("day", 1),
                    hour=12,
                    tzinfo=timezone.utc
                )
                
                event = SeasonalEvent(
                    name=item["name"],
                    event_date=event_date,
                    recurrence="yearly",
                    niche=item["niche"],
                    description=item.get("description", ""),
                    peak_anticipation_days=21  # 3 weeks ahead
                )
                db.add(event)
                seeded_count += 1

        await db.commit()
        return seeded_count

    async def get_upcoming_unplanned_events(self, db: AsyncSession, lookahead_days: int = 21) -> list[SeasonalEvent]:
        """Fetch all upcoming events in the next N days that lack a scheduled content plan."""
        now = datetime.now(timezone.utc)
        target_max_date = now + timedelta(days=lookahead_days)
        
        # Query events occurring between now and target date
        query = select(SeasonalEvent).where(
            SeasonalEvent.event_date >= now,
            SeasonalEvent.event_date <= target_max_date
        )
        res = await db.execute(query)
        upcoming = res.scalars().all()

        unplanned = []
        for event in upcoming:
            # Check if EventContentPlan exists
            plan_res = await db.execute(
                select(EventContentPlan).where(EventContentPlan.event_id == event.id)
            )
            if not plan_res.scalar_one_or_none():
                unplanned.append(event)
                
        return unplanned

    async def create_seasonal_brief(self, db: AsyncSession, event_id: uuid.UUID) -> ContentBrief:
        """Create a targeted ContentBrief tied to a seasonal event."""
        # 1. Fetch event
        event_res = await db.execute(select(SeasonalEvent).where(SeasonalEvent.id == event_id))
        event = event_res.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        # 2. Create a Topic object to act as database pivot
        topic = Topic(
            title=f"Preparing for {event.name}",
            description=f"Automated seasonal guide mapping topics for {event.name}. {event.description}",
            composite_score=85.0,
            status=TopicStatus.ACCEPTED
        )
        db.add(topic)
        await db.flush()

        # 3. Generate content brief
        brief = ContentBrief(
            topic_id=topic.id,
            format="offer" if event.niche == "sales" else "educational",
            target_emotion="excitement" if event.niche == "sales" else "inspiration",
            target_platforms=["youtube", "tiktok", "instagram", "twitter", "linkedin"],
            talking_points={"bullets": [f"Introduction to {event.name}", "Common mistakes to avoid", "Top 3 recommendations"]},
            cta_strategy="Sign up for our email newsletter to get live updates during the event."
        )
        db.add(brief)
        await db.flush()

        # 4. Save Event Content Plan link
        plan = EventContentPlan(
            event_id=event.id,
            brief_id=brief.id
        )
        db.add(plan)
        await db.commit()
        await db.refresh(brief)
        
        return brief
