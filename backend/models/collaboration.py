"""Database models for community collaboration and lead tracking (Tier E)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CollabTarget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A target creator or brand for audience-building outreach."""

    __tablename__ = "collab_targets"

    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    niche_overlap: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0 to 1
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)  # discovered, approved, blacklisted
    outreach_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, draft_written, sent, warm, dead

    # ── Relationships ─────────────────────────────────────────────────────
    drafts: Mapped[list[OutreachDraft]] = relationship(
        "OutreachDraft", back_populates="target", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CollabTarget {self.handle!r} platform={self.platform!r}>"


class OutreachDraft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Outreach template drafted in the creator's persona for direct messaging/email."""

    __tablename__ = "outreach_drafts"

    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collab_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    target: Mapped[CollabTarget] = relationship("CollabTarget", back_populates="drafts")

    def __repr__(self) -> str:
        return f"<OutreachDraft target={self.target_id} sent={self.sent_at is not None}>"


class FunnelStage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audience members tracked through comment-to-DM or comment-to-email conversion paths."""

    __tablename__ = "funnel_stages"

    email_contact: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), default="lead", nullable=False)  # lead, dm_sent, email_submitted, customer
    estimated_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    def __repr__(self) -> str:
        return f"<FunnelStage username={self.username!r} stage={self.stage!r}>"
