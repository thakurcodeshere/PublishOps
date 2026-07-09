"""Database models for content arc planning and platform syndication mix (Tier B)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentArc(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A multi-week content campaign arc designed to build audience context."""

    __tablename__ = "content_arcs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, completed, draft

    # ── Relationships ─────────────────────────────────────────────────────
    segments: Mapped[list[ArcSegment]] = relationship(
        "ArcSegment", back_populates="arc", cascade="all, delete-orphan"
    )
    mix_target: Mapped[ContentMixTarget | None] = relationship(
        "ContentMixTarget", back_populates="arc", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContentArc {self.name!r} status={self.status!r}>"


class ArcSegment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single weekly block of content within a larger campaign arc."""

    __tablename__ = "arc_segments"

    arc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_arcs.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_brief_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # list of brief UUIDs mapped to platforms

    # ── Relationships ─────────────────────────────────────────────────────
    arc: Mapped[ContentArc] = relationship("ContentArc", back_populates="segments")

    def __repr__(self) -> str:
        return f"<ArcSegment week={self.week_number} title={self.title!r}>"


class ContentMixTarget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Enforces thematic diversity targets (e.g. 40/30/20/10 rule)."""

    __tablename__ = "content_mix_targets"

    arc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_arcs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    educational_pct: Mapped[float] = mapped_column(Float, default=0.40, nullable=False)    # 40% Education
    entertainment_pct: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)  # 30% Entertainment/Hype
    personal_story_pct: Mapped[float] = mapped_column(Float, default=0.20, nullable=False) # 20% Personal/Story
    offer_pct: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)          # 10% Pitch/Conversion

    # ── Relationships ─────────────────────────────────────────────────────
    arc: Mapped[ContentArc] = relationship("ContentArc", back_populates="mix_target")


from typing import Any # noqa: E402
