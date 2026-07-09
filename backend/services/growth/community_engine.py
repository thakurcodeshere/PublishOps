"""Community and Collaboration Engine service (Tier E) to draft partner outreach in creator's voice."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.collaboration import CollabTarget, OutreachDraft
from backend.models.creator_profile import CreatorProfile

logger = logging.getLogger(__name__)


class CommunityEngine:
    """Orchestrates influencer/creator collaborations and drafts personalized outreach."""

    async def add_collaboration_target(
        self,
        db: AsyncSession,
        handle: str,
        platform: str,
        follower_count: int,
        niche_overlap: float = 0.5
    ) -> CollabTarget:
        """Register a new potential collaborator target."""
        target = CollabTarget(
            handle=handle,
            platform=platform,
            follower_count=follower_count,
            niche_overlap=niche_overlap,
            status="discovered",
            outreach_status="pending"
        )
        db.add(target)
        await db.commit()
        await db.refresh(target)
        return target

    async def draft_outreach(self, db: AsyncSession, creator_id: uuid.UUID, target_id: uuid.UUID) -> OutreachDraft:
        """Draft a collaboration pitch DM to a target creator, locked to the creator's persona style."""
        # 1. Fetch target and creator
        target_res = await db.execute(select(CollabTarget).where(CollabTarget.id == target_id))
        target = target_res.scalar_one_or_none()
        if not target:
            raise ValueError("Collaboration target not found")
            
        creator_res = await db.execute(select(CreatorProfile).where(CreatorProfile.id == creator_id))
        creator = creator_res.scalar_one_or_none()
        if not creator:
            raise ValueError("Creator profile not found")

        # 2. Extract style parameters for custom template assembly
        contractions_enabled = True
        fillers = ["um", "like"]
        
        if creator.lexical:
            lex = creator.lexical.profile_data
            contractions_enabled = lex.get("contractions_ratio", 0.05) > 0.02
            fillers = list(lex.get("filler_words", {}).keys()) or fillers

        # Base outreach template variations
        if target.platform.lower() in ["twitter", "x"]:
            # Short DM format
            msg = f"Hey @{target.handle} - loved your recent post on dev workflows. "
            if contractions_enabled:
                msg += "I'm building an automation pipeline that makes cross-posting a breeze. "
            else:
                msg += "I am building an automation pipeline that makes cross-posting a breeze. "
            msg += f"Would love to show you a quick preview sometime if you're open to it?"
        else:
            # Longer email/DM format
            msg = f"Hey {target.handle},\n\n"
            msg += "Hope you are doing great. I have been following your content for a while and "
            msg += "really enjoy your breakdowns of tech architecture.\n\n"
            if contractions_enabled:
                msg += "I'm working on a content engine called PublishOps, and I think your audience "
                msg += "would get a ton of value from a joint session on database scaling. "
            else:
                msg += "I am working on a content engine called PublishOps, and I think your audience "
                msg += "would get a ton of value from a joint session on database scaling. "
            msg += "Let me know if you might be open to co-producing a video on this!\n\nBest,\n"
            msg += creator.name

        # Save outreach draft
        draft = OutreachDraft(
            target_id=target.id,
            draft_text=msg
        )
        db.add(draft)
        
        # Update target outreach status
        target.outreach_status = "draft_written"
        db.add(target)
        
        await db.commit()
        await db.refresh(draft)
        return draft
