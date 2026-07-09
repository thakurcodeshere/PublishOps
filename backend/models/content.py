"""Content models — briefs and production assets."""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BriefStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(str, enum.Enum):
    SCRIPT = "script"
    AUDIO_RAW = "audio_raw"
    AUDIO_ENHANCED = "audio_enhanced"
    VIDEO_CLIP = "video_clip"
    VIDEO_ASSEMBLED = "video_assembled"
    THUMBNAIL = "thumbnail"
    SUBTITLE = "subtitle"


class AssetStage(str, enum.Enum):
    SCRIPT = "script"
    VOICE = "voice"
    AUDIO_ENHANCE = "audio_enhance"
    VIDEO_GEN = "video_gen"
    ASSEMBLY = "assembly"
    THUMBNAIL = "thumbnail"
    COMPLETE = "complete"


class AssetStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentBrief(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A production brief generated from a scored topic."""

    __tablename__ = "content_briefs"

    topic_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    hook_id: Mapped["uuid.UUID | None"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hooks.id", ondelete="SET NULL"), nullable=True
    )
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    target_emotion: Mapped[str] = mapped_column(String(50), nullable=False)
    target_platforms: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    talking_points: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cta_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    variants_planned: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    brief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus, name="brief_status"),
        default=BriefStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────
    topic: Mapped["Topic"] = relationship("Topic", back_populates="briefs")  # noqa: F821
    hook: Mapped["Hook | None"] = relationship("Hook")  # noqa: F821
    assets: Mapped[list["ContentAsset"]] = relationship(
        "ContentAsset", back_populates="brief", cascade="all, delete-orphan"
    )
    variants: Mapped[list["PlatformVariant"]] = relationship(  # noqa: F821
        "PlatformVariant", back_populates="brief", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContentBrief {self.format!r} status={self.status.value}>"


class ContentAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A produced content asset (audio, video, thumbnail, etc.)."""

    __tablename__ = "content_assets"

    brief_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type"), nullable=False
    )
    s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    s3_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_secs: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    stage: Mapped[AssetStage] = mapped_column(
        Enum(AssetStage, name="asset_stage"),
        default=AssetStage.SCRIPT,
        nullable=False,
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status"),
        default=AssetStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    brief: Mapped["ContentBrief"] = relationship("ContentBrief", back_populates="assets")
    variants: Mapped[list["PlatformVariant"]] = relationship(  # noqa: F821
        "PlatformVariant", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContentAsset {self.asset_type.value} stage={self.stage.value}>"


# Ensure uuid import is available for type hints
import uuid  # noqa: E402
