"""Database models for revenue attribution and conversion event mapping (Tier E)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RevenueEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Raw transaction events scraped or webhook-delivered from Stripe, Gumroad, or Shopify."""

    __tablename__ = "revenue_events"

    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # stripe, shopify, gumroad
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<RevenueEvent tx={self.transaction_id} amount={self.amount} {self.currency}>"


class ContentRevenue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Aggregated financial returns attributed to a specific ContentBrief."""

    __tablename__ = "content_revenue"

    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    revenue_attributed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    conversion_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────
    brief: Mapped["ContentBrief"] = relationship("ContentBrief")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ContentRevenue brief={self.brief_id} revenue={self.revenue_attributed:.2f}>"


class AttributionLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maintains mapping of specific UTM campaign tags to content items for tracking clicks."""

    __tablename__ = "attribution_links"

    utm_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # unique campaign tag
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    def __repr__(self) -> str:
        return f"<AttributionLink code={self.utm_code!r} brief={self.brief_id}>"


import sqlalchemy as sa  # noqa: E402
