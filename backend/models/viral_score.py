"""Database models for Viral Score Gate classification logs and versioning (Tier B)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ViralScoreResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The predictive score computed for a brief or script before production."""

    __tablename__ = "viral_score_results"

    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    ctr_prediction: Mapped[float] = mapped_column(Float, nullable=False)          # Estimated Click-Through Rate (e.g. 0-100)
    watch_time_prediction: Mapped[float] = mapped_column(Float, nullable=False)   # Estimated retention/watch-time % (e.g. 0-100)
    engagement_prediction: Mapped[float] = mapped_column(Float, nullable=False)   # Estimated engagement score (e.g. 0-100)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)         # Overall rating
    
    passed_gate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    brief: Mapped["ContentBrief"] = relationship("ContentBrief")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ViralScoreResult brief={self.brief_id} score={self.composite_score:.1f} passed={self.passed_gate}>"


class ViralModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks training versions and offline accuracy metrics of the Viral Predictor."""

    __tablename__ = "viral_model_versions"

    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    accuracy_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # RMSE, precision/recall, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<ViralModelVersion v={self.version} active={self.is_active}>"
