"""Database models for seasonal event calendars and automated planning (Tier E)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SeasonalEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A recurring cultural, industry, or promotional calendar event."""

    __tablename__ = "seasonal_events"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recurrence: Mapped[str] = mapped_column(String(50), default="yearly", nullable=False)  # yearly, monthly, once
    niche: Mapped[str] = mapped_column(String(100), nullable=False)  # technology, general, sales
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    peak_anticipation_days: Mapped[int] = mapped_column(Integer, default=21, nullable=False)  # target production start buffer

    # ── Relationships ─────────────────────────────────────────────────────
    content_plans: Mapped[list[EventContentPlan]] = relationship(
        "EventContentPlan", back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SeasonalEvent {self.name!r} date={self.event_date.strftime('%Y-%m-%d')}>"


class EventContentPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maps a seasonal event directly to a planned content brief."""

    __tablename__ = "event_content_plans"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seasonal_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    event: Mapped[SeasonalEvent] = relationship("SeasonalEvent", back_populates="content_plans")
    brief: Mapped["ContentBrief"] = relationship("ContentBrief")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EventContentPlan event={self.event_id} brief={self.brief_id}>"
