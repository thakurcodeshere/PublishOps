"""Topic model — discovered trending topics with composite scoring."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TopicStatus(str, enum.Enum):
    """Lifecycle status of a discovered topic."""

    DISCOVERED = "discovered"
    SCORED = "scored"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BRIEF_CREATED = "brief_created"
    IN_PRODUCTION = "in_production"
    PUBLISHED = "published"
    EXPIRED = "expired"


class Topic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A trending topic discovered by the intelligence engine."""

    __tablename__ = "topics"

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Scoring ───────────────────────────────────────────────────────────
    composite_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    velocity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evergreen_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    platform_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    saturation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # ── Metadata ──────────────────────────────────────────────────────────
    status: Mapped[TopicStatus] = mapped_column(
        Enum(TopicStatus, name="topic_status"),
        default=TopicStatus.DISCOVERED,
        nullable=False,
        index=True,
    )
    source_apis: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    briefs: Mapped[list["ContentBrief"]] = relationship(  # noqa: F821
        "ContentBrief", back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic {self.title!r} score={self.composite_score:.1f}>"
