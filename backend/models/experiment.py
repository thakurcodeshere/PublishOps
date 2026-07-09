"""Database models for content A/B experiments and self-learning formats (Tier F)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Experiment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A controlled content format or title test running over a period."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)  # running, completed
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    format_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # modified parameters

    # ── Relationships ─────────────────────────────────────────────────────
    results: Mapped[list[ExperimentResult]] = relationship(
        "ExperimentResult", back_populates="experiment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Experiment {self.name!r} status={self.status!r}>"


class ExperimentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Log of post variant performance relative to the baseline control."""

    __tablename__ = "experiment_results"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    metric_improvement_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="results")
    variant: Mapped["PlatformVariant"] = relationship("PlatformVariant")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ExperimentResult exp={self.experiment_id} winner={self.is_winner}>"


import sqlalchemy as sa  # noqa: E402
