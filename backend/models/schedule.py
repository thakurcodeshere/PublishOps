"""Upload schedule model — manages timed posting across platforms."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScheduleStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    UPLOADING = "uploading"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A scheduled upload for a platform variant."""

    __tablename__ = "upload_schedule"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    jitter_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    platform_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status"),
        default=ScheduleStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_edit_applied: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    post_edit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    variant: Mapped["PlatformVariant"] = relationship(  # noqa: F821
        "PlatformVariant", back_populates="schedules"
    )

    def __repr__(self) -> str:
        return f"<UploadSchedule {self.platform} at={self.scheduled_at}>"
