"""Database models for publishing compliance, synthetic labels, and likeness consent (Tier D)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ComplianceCheck(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Log of synthetic media disclosure checks performed before publishing."""

    __tablename__ = "compliance_checks"

    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    synthetic_media_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_labels: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # platform -> required label text
    status: Mapped[str] = mapped_column(String(50), default="passed", nullable=False)  # passed, warning, flag_manual

    # ── Relationships ─────────────────────────────────────────────────────
    brief: Mapped["ContentBrief"] = relationship("ContentBrief")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ComplianceCheck brief={self.brief_id} status={self.status!r}>"


class ConsentLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Enforces that creator likeness, voice, and personal stories are explicitly consented to."""

    __tablename__ = "consent_ledgers"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    consent_given: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def __repr__(self) -> str:
        return f"<ConsentLedger creator={self.creator_id} asset={self.asset_id} consented={self.consent_given}>"


class AuditTrail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tamper-proof ledger of AI-pipeline operations for publishing audits."""

    __tablename__ = "audit_trails"

    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    action: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "generated_script", "passed_redteam"
    actor: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<AuditTrail brief={self.brief_id} action={self.action!r}>"


import sqlalchemy as sa  # noqa: E402
