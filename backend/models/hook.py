"""Hook model — reusable opening hooks with performance tracking."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Hook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A reusable content hook with performance metrics."""

    __tablename__ = "hooks"

    text: Mapped[str] = mapped_column(Text, nullable=False)
    hook_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # question, stat, story, bold_claim, analogy
    target_emotion: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # curiosity, fomo, urgency, inspiration, outrage, amusement
    platform_affinity: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # {"youtube": 0.8, "tiktok": 0.9, ...}
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_performance: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Hook {self.hook_type!r} perf={self.avg_performance:.2f}>"
