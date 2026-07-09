"""Database models for audience vocabulary mining and phrasal analysis (Tier A)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AudiencePhrase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A specific phrase, question, or comment extracted from audience channels."""

    __tablename__ = "audience_phrases"

    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)  # reddit, youtube, etc.
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    pain_point_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<AudiencePhrase platform={self.source_platform!r} pain_point={self.pain_point_flag}>"


class VocabCluster(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A clustered group of semantically similar audience phrases."""

    __tablename__ = "vocab_clusters"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phrases: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # list of strings/phrases
    representative_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    target_persona: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<VocabCluster {self.name!r}>"
