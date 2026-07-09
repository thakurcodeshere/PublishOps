"""Opinion store service (Tier C) for managing the creator's Voice Bible and system prompt constraints."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.creator_profile import OpinionEntry


class OpinionStore:
    """Manages CRUD for the Voice Bible and generates prompt constraint blocks."""

    async def add_opinion(
        self,
        db: AsyncSession,
        creator_id: uuid.UUID,
        topic: str,
        stance: str,
        allowed_terms: list[str] | None = None,
        forbidden_terms: list[str] | None = None,
    ) -> OpinionEntry:
        """Add a stance/opinion entry to the creator's Voice Bible."""
        entry = OpinionEntry(
            creator_id=creator_id,
            topic=topic,
            stance=stance,
            allowed_terms={"terms": allowed_terms or []},
            forbidden_terms={"terms": forbidden_terms or []},
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def get_opinions(self, db: AsyncSession, creator_id: uuid.UUID) -> list[OpinionEntry]:
        """Retrieve all Voice Bible entries for a creator."""
        result = await db.execute(
            select(OpinionEntry).where(OpinionEntry.creator_id == creator_id)
        )
        return list(result.scalars().all())

    async def delete_opinion(self, db: AsyncSession, opinion_id: uuid.UUID) -> bool:
        """Delete an opinion entry by ID."""
        await db.execute(delete(OpinionEntry).where(OpinionEntry.id == opinion_id))
        await db.commit()
        return True

    async def update_opinion(
        self,
        db: AsyncSession,
        opinion_id: uuid.UUID,
        stance: str | None = None,
        allowed_terms: list[str] | None = None,
        forbidden_terms: list[str] | None = None,
    ) -> OpinionEntry | None:
        """Update an existing opinion entry."""
        result = await db.execute(select(OpinionEntry).where(OpinionEntry.id == opinion_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        if stance is not None:
            entry.stance = stance
        if allowed_terms is not None:
            entry.allowed_terms = {"terms": allowed_terms}
        if forbidden_terms is not None:
            entry.forbidden_terms = {"terms": forbidden_terms}

        await db.commit()
        await db.refresh(entry)
        return entry

    async def get_voice_bible_prompt_constraints(self, db: AsyncSession, creator_id: uuid.UUID) -> str:
        """Generate a system prompt block enforcing Voice Bible stances and vocabulary rules."""
        opinions = await self.get_opinions(db, creator_id)
        if not opinions:
            return ""

        lines = [
            "### CREATOR PERSONA & VOICE BIBLE CONSTRAINTS",
            "Write the script using the creator's explicit stances and vocabulary rules below.",
            "Do NOT deviate from these stances or use the forbidden terms.",
            "",
        ]

        # Aggregate forbidden phrases across all entries
        all_forbidden = set()
        
        for entry in opinions:
            lines.append(f"- **On {entry.topic}**: {entry.stance}")
            
            allowed = entry.allowed_terms.get("terms", [])
            if allowed:
                lines.append(f"  * Preferred phrasing/keywords: {', '.join(allowed)}")
                
            forbidden = entry.forbidden_terms.get("terms", [])
            for term in forbidden:
                all_forbidden.add(term)

        # Standard AI clichés that are universally forbidden if none specified, otherwise add them
        all_forbidden.update(["delve", "testament", "tapestry", "moreover", "furthermore", "in conclusion"])
        
        if all_forbidden:
            lines.append("")
            lines.append("### FORBIDDEN WORDS / AI CLICHÉS")
            lines.append("NEVER use the following words or phrases in the script:")
            lines.append(f"  {', '.join(sorted(all_forbidden))}")

        return "\n".join(lines)
