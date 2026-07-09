"""Platform variant model — per-platform repackaged content."""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VariantStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    UPLOADED = "uploaded"
    FAILED = "failed"


class PlatformVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Platform-specific variant of a content asset."""

    __tablename__ = "platform_variants"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aspect_ratio: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    specs: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[VariantStatus] = mapped_column(
        Enum(VariantStatus, name="variant_status"),
        default=VariantStatus.PENDING,
        nullable=False,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    asset: Mapped["ContentAsset"] = relationship(  # noqa: F821
        "ContentAsset", back_populates="variants"
    )
    brief: Mapped["ContentBrief"] = relationship(  # noqa: F821
        "ContentBrief", back_populates="variants"
    )
    schedules: Mapped[list["UploadSchedule"]] = relationship(  # noqa: F821
        "UploadSchedule", back_populates="variant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PlatformVariant {self.platform} {self.aspect_ratio}>"
