"""Analytics models — snapshots, scoring weights, and platform rules."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsSnapshot(Base, UUIDPrimaryKeyMixin):
    """Point-in-time metrics snapshot for a platform variant."""

    __tablename__ = "analytics_snapshots"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    days_since_post: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ScoringWeight(Base, UUIDPrimaryKeyMixin):
    """Current and historical scoring weight configurations."""

    __tablename__ = "scoring_weights"

    velocity_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    evergreen_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    fit_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    saturation_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    performance_delta: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PlatformRule(Base, UUIDPrimaryKeyMixin):
    """Platform algorithm signal rules and optimization notes."""

    __tablename__ = "platform_rules"

    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signal_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimization_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
