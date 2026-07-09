"""Database models for creator profiles and calibration data (Tier C)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Main creator profile linking all calibration channels."""

    __tablename__ = "creator_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    lexical: Mapped[LexicalProfile | None] = relationship(
        "LexicalProfile", back_populates="creator", uselist=False, cascade="all, delete-orphan"
    )
    cadence: Mapped[CadenceProfile | None] = relationship(
        "CadenceProfile", back_populates="creator", uselist=False, cascade="all, delete-orphan"
    )
    acoustic: Mapped[AcousticProfile | None] = relationship(
        "AcousticProfile", back_populates="creator", uselist=False, cascade="all, delete-orphan"
    )
    disfluency: Mapped[DisfluencyProfile | None] = relationship(
        "DisfluencyProfile", back_populates="creator", uselist=False, cascade="all, delete-orphan"
    )
    temporal: Mapped[TemporalProfile | None] = relationship(
        "TemporalProfile", back_populates="creator", uselist=False, cascade="all, delete-orphan"
    )
    opinions: Mapped[list[OpinionEntry]] = relationship(
        "OpinionEntry", back_populates="creator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CreatorProfile {self.name!r}>"


class LexicalProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Lexical channel: NLP profiling of writing style, vocabulary, filler patterns."""

    __tablename__ = "lexical_profiles"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    # Store lexical metadata: vocabulary frequency, filler words count, contractions ratio,
    # sentence length distributions, readability metrics, readability score.
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="lexical")


class CadenceProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Cadence channel: Speech WPM curves, pause durations, speech rate variation."""

    __tablename__ = "cadence_profiles"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Store cadence data: WPM curves, pause-length histograms, variance metrics.
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="cadence")


class AcousticProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Acoustic channel: Breath placement, pitch drift (jitter), background noise, mic profile."""

    __tablename__ = "acoustic_profiles"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Store acoustic metrics: breath positions, room tone spectral profile, pitch drift, noise floor.
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="acoustic")


class DisfluencyProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Disfluency channel: stumble rate, filler word placements, verbal ticks."""

    __tablename__ = "disfluency_profiles"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Store disfluency data: target stumbles/min (e.g. 2-4), disfluency types distribution.
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="disfluency")


class TemporalProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Temporal channel: Historical publishing time patterns, day-of-week preference, jitter limits."""

    __tablename__ = "temporal_profiles"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Store scheduling temporal data: posting patterns, peak activity times, dynamic jitter offsets.
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="temporal")


class OpinionEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Opinion/Voice Bible: beliefs, stances, topics, forbidden phrases/concepts."""

    __tablename__ = "opinion_entries"

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    stance: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_terms: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # list of key phrases/terms
    forbidden_terms: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # list of words/phrases to avoid

    # ── Relationships ─────────────────────────────────────────────────────
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile", back_populates="opinions")

    def __repr__(self) -> str:
        return f"<OpinionEntry topic={self.topic!r}>"
