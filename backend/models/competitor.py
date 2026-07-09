"""Database models for competitor tracking and coverage analysis (Tier A)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Competitor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tracked competitor profile."""

    __tablename__ = "competitors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # youtube, tiktok, etc.
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    content: Mapped[list[CompetitorContent]] = relationship(
        "CompetitorContent", back_populates="competitor", cascade="all, delete-orphan"
    )
    gaps: Mapped[list[CoverageMatrix]] = relationship(
        "CoverageMatrix", back_populates="competitor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competitor {self.name!r} platform={self.platform!r}>"


class CompetitorContent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Historical post or video from a competitor."""

    __tablename__ = "competitor_content"

    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    competitor: Mapped[Competitor] = relationship("Competitor", back_populates="content")

    def __repr__(self) -> str:
        return f"<CompetitorContent platform={self.platform!r} url={self.url!r}>"


class CoverageMatrix(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Density score of topic coverage by a competitor."""

    __tablename__ = "coverage_matrices"

    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    keyword_cluster: Mapped[str] = mapped_column(String(255), nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0 to 1
    demand_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)    # 0 to 1
    gap_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)       # demand - coverage

    # ── Relationships ─────────────────────────────────────────────────────
    competitor: Mapped[Competitor] = relationship("Competitor", back_populates="gaps")

    def __repr__(self) -> str:
        return f"<CoverageMatrix cluster={self.keyword_cluster!r} gap={self.gap_score:.2f}>"
