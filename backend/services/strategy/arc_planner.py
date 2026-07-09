"""Narrative Arc Planner service (Tier B) to schedule structured content campaigns over weeks."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import ContentBrief, BriefStatus
from backend.models.content_arc import ArcSegment, ContentArc, ContentMixTarget
from backend.models.topic import Topic


class NarrativeArcPlanner:
    """Plans multi-week content campaigns, assigning topics to match target category distributions."""

    async def create_content_arc(
        self,
        db: AsyncSession,
        name: str,
        target_audience: str,
        duration_weeks: int = 4,
        mix_data: dict[str, float] | None = None
    ) -> ContentArc:
        """Create a new content arc and set up its weekly segments and mix targets."""
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(weeks=duration_weeks)

        # 1. Create Arc
        arc = ContentArc(
            name=name,
            target_audience=target_audience,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        db.add(arc)
        await db.flush()  # get arc.id

        # 2. Create Mix Target
        mix = mix_data or {}
        mix_target = ContentMixTarget(
            arc_id=arc.id,
            educational_pct=mix.get("educational_pct", 0.40),
            entertainment_pct=mix.get("entertainment_pct", 0.30),
            personal_story_pct=mix.get("personal_story_pct", 0.20),
            offer_pct=mix.get("offer_pct", 0.10)
        )
        db.add(mix_target)

        # 3. Create weekly segments
        for w in range(1, duration_weeks + 1):
            segment = ArcSegment(
                arc_id=arc.id,
                title=f"Week {w}: {name} Sub-topic",
                week_number=w,
                content_brief_ids={"briefs": []}
            )
            db.add(segment)

        await db.commit()
        await db.refresh(arc)
        return arc

    async def distribute_topics_into_arc(
        self,
        db: AsyncSession,
        arc_id: uuid.UUID,
        topics: list[Topic]
    ) -> list[ContentBrief]:
        """Distribute topics into weekly segments of the arc while enforcing the content mix.
        
        Creates ContentBrief objects for each assigned topic.
        """
        # Fetch the arc and its segments
        arc_query = await db.execute(select(ContentArc).where(ContentArc.id == arc_id))
        arc = arc_query.scalar_one_or_none()
        if not arc:
            raise ValueError("Content arc not found")
            
        segments_query = await db.execute(
            select(ArcSegment).where(ArcSegment.arc_id == arc_id).order_by(ArcSegment.week_number)
        )
        segments = list(segments_query.scalars().all())
        
        mix = arc.mix_target
        if not mix:
            # Fallback default mix
            mix = ContentMixTarget(
                arc_id=arc_id,
                educational_pct=0.40,
                entertainment_pct=0.30,
                personal_story_pct=0.20,
                offer_pct=0.10
            )

        # Map counts of topics we need to create
        total_slots = len(segments) * 2  # assume 2 posts/briefs per week
        num_edu = max(1, int(total_slots * mix.educational_pct))
        num_ent = max(1, int(total_slots * mix.entertainment_pct))
        num_story = max(1, int(total_slots * mix.personal_story_pct))
        num_offer = total_slots - (num_edu + num_ent + num_story)
        if num_offer < 0:
            num_offer = 0

        # Construct list of formats/types to distribute
        formats = (
            ["educational"] * num_edu +
            ["entertainment"] * num_ent +
            ["personal_story"] * num_story +
            ["offer"] * num_offer
        )
        random.shuffle(formats)

        created_briefs = []
        topic_idx = 0
        
        # Distribute into segments
        for seg in segments:
            brief_ids = []
            
            # Create 2 briefs for this week
            for _ in range(2):
                if topic_idx >= len(topics):
                    break
                topic = topics[topic_idx]
                topic_idx += 1
                
                # Determine format
                fmt = formats.pop() if formats else "educational"

                # Define strategy details based on category
                target_emotion = "curiosity"
                cta = "Read more in the link below."
                if fmt == "educational":
                    target_emotion = "inspiration"
                    cta = "Save this post for reference."
                elif fmt == "entertainment":
                    target_emotion = "excitement"
                    cta = "Share this with a friend who needs to hear it."
                elif fmt == "personal_story":
                    target_emotion = "empathy"
                    cta = "Comment your thoughts below."
                elif fmt == "offer":
                    target_emotion = "urgency"
                    cta = "Click the bio link to join the waitlist."

                brief = ContentBrief(
                    topic_id=topic.id,
                    format=fmt,
                    target_emotion=target_emotion,
                    target_platforms=["youtube", "tiktok", "instagram", "twitter", "linkedin"],
                    talking_points={"bullets": [f"Key concept of {topic.title}", "Actionable step", "Key take-away"]},
                    cta_strategy=cta,
                    status=BriefStatus.DRAFT
                )
                db.add(brief)
                await db.flush()  # get brief.id
                
                brief_ids.append(str(brief.id))
                created_briefs.append(brief)
                
            seg.content_brief_ids = {"briefs": brief_ids}
            db.add(seg)

        await db.commit()
        return created_briefs
