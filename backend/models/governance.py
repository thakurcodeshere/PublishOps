"""Database models for system reliability, service health, and API cost tracking (Tier F)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PipelineIncident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logs system failures or exceptions to halt downstream actions automatically."""

    __tablename__ = "pipeline_incidents"

    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    error_msg: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, resolved
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<PipelineIncident stage={self.stage!r} status={self.status!r}>"


class CostLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks LLM, audio generation, and deepfake detector API expenditures."""

    __tablename__ = "cost_ledgers"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False)  # anthropic, elevenlabs, gptzero, etc.
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def __repr__(self) -> str:
        return f"<CostLedger service={self.service_name!r} cost=${self.amount_usd:.4f}>"


class ServiceHealth(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks latency and availability of downstream APIs to predict failures."""

    __tablename__ = "service_health"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def __repr__(self) -> str:
        return f"<ServiceHealth service={self.service_name!r} active={self.is_active} latency={self.latency_ms}ms>"


import sqlalchemy as sa  # noqa: E402
