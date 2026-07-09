"""Initial schema — all tables, indexes, and default scoring weights.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-06-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────
    topic_status = postgresql.ENUM(
        "discovered", "scored", "accepted", "rejected",
        "brief_created", "in_production", "published", "expired",
        name="topic_status",
        create_type=False,
    )
    brief_status = postgresql.ENUM(
        "draft", "approved", "in_production", "completed", "failed",
        name="brief_status",
        create_type=False,
    )
    asset_type = postgresql.ENUM(
        "script", "audio_raw", "audio_enhanced", "video_clip",
        "video_assembled", "thumbnail", "subtitle",
        name="asset_type",
        create_type=False,
    )
    asset_stage = postgresql.ENUM(
        "script", "voice", "audio_enhance", "video_gen",
        "assembly", "thumbnail", "complete",
        name="asset_stage",
        create_type=False,
    )
    asset_status = postgresql.ENUM(
        "pending", "processing", "completed", "failed",
        name="asset_status",
        create_type=False,
    )
    variant_status = postgresql.ENUM(
        "pending", "processing", "ready", "uploaded", "failed",
        name="variant_status",
        create_type=False,
    )
    schedule_status = postgresql.ENUM(
        "scheduled", "queued", "uploading", "posted", "failed", "cancelled",
        name="schedule_status",
        create_type=False,
    )

    # Create enum types first
    for enum_type in [
        topic_status, brief_status, asset_type, asset_stage,
        asset_status, variant_status, schedule_status,
    ]:
        enum_type.create(op.get_bind(), checkfirst=True)

    # ── topics ────────────────────────────────────────────────────────────
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("composite_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("velocity_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evergreen_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("platform_fit", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("saturation", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "status",
            topic_status,
            nullable=False,
            server_default="discovered",
            index=True,
        ),
        sa.Column("source_apis", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("raw_data", postgresql.JSONB, nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── hooks ─────────────────────────────────────────────────────────────
    op.create_table(
        "hooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("hook_type", sa.String(50), nullable=False, index=True),
        sa.Column("target_emotion", sa.String(50), nullable=False),
        sa.Column("platform_affinity", postgresql.JSONB, nullable=True),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_performance", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── content_briefs ────────────────────────────────────────────────────
    op.create_table(
        "content_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "topic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "hook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hooks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("target_emotion", sa.String(50), nullable=False),
        sa.Column("target_platforms", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("talking_points", postgresql.JSONB, nullable=True),
        sa.Column("cta_strategy", sa.Text, nullable=True),
        sa.Column("variants_planned", sa.Integer, nullable=False, server_default="6"),
        sa.Column("brief_text", sa.Text, nullable=True),
        sa.Column(
            "status",
            brief_status,
            nullable=False,
            server_default="draft",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── content_assets ────────────────────────────────────────────────────
    op.create_table(
        "content_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("s3_key", sa.String(1024), nullable=True),
        sa.Column("s3_url", sa.String(2048), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("duration_secs", sa.Float, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "stage",
            asset_stage,
            nullable=False,
            server_default="script",
        ),
        sa.Column(
            "status",
            asset_status,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("error_log", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── platform_variants ─────────────────────────────────────────────────
    op.create_table(
        "platform_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False, index=True),
        sa.Column("aspect_ratio", sa.String(10), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("hashtags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("s3_key", sa.String(1024), nullable=True),
        sa.Column("specs", postgresql.JSONB, nullable=True),
        sa.Column(
            "status",
            variant_status,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── upload_schedule ───────────────────────────────────────────────────
    op.create_table(
        "upload_schedule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False, index=True),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("jitter_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("actual_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_post_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            schedule_status,
            nullable=False,
            server_default="scheduled",
            index=True,
        ),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_log", sa.Text, nullable=True),
        sa.Column("post_edit_applied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("post_edit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── analytics_snapshots ───────────────────────────────────────────────
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("platform", sa.String(50), nullable=False, index=True),
        sa.Column("days_since_post", sa.Integer, nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False),
        sa.Column(
            "snapshot_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── scoring_weights ───────────────────────────────────────────────────
    op.create_table(
        "scoring_weights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("velocity_weight", sa.Float, nullable=False, server_default="0.4"),
        sa.Column("evergreen_weight", sa.Float, nullable=False, server_default="0.3"),
        sa.Column("fit_weight", sa.Float, nullable=False, server_default="0.2"),
        sa.Column("saturation_weight", sa.Float, nullable=False, server_default="0.1"),
        sa.Column("performance_delta", sa.Float, nullable=True, server_default="0.0"),
        sa.Column("iteration", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── platform_rules ────────────────────────────────────────────────────
    op.create_table(
        "platform_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(50), nullable=False, index=True),
        sa.Column("signal_name", sa.String(200), nullable=False),
        sa.Column("signal_weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("optimization_notes", sa.Text, nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── repost_queue (lightweight tracking table) ─────────────────────────
    op.create_table(
        "repost_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_variants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "original_schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_schedule.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("engagement_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("refreshed_title", sa.String(500), nullable=True),
        sa.Column("refreshed_caption", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="'pending'"),
        sa.Column(
            "identified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("repost_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── Additional composite indexes ──────────────────────────────────────
    op.create_index(
        "ix_topics_score_status",
        "topics",
        ["composite_score", "status"],
    )
    op.create_index(
        "ix_topics_discovered_score",
        "topics",
        ["discovered_at", "composite_score"],
    )
    op.create_index(
        "ix_content_briefs_topic_status",
        "content_briefs",
        ["topic_id", "status"],
    )
    op.create_index(
        "ix_content_assets_brief_status",
        "content_assets",
        ["brief_id", "status"],
    )
    op.create_index(
        "ix_platform_variants_platform_status",
        "platform_variants",
        ["platform", "status"],
    )
    op.create_index(
        "ix_upload_schedule_platform_status",
        "upload_schedule",
        ["platform", "status"],
    )
    op.create_index(
        "ix_analytics_snapshots_variant_platform",
        "analytics_snapshots",
        ["variant_id", "platform"],
    )
    op.create_index(
        "ix_analytics_snapshots_snapshot_at",
        "analytics_snapshots",
        ["snapshot_at"],
    )

    # ── Insert default scoring weights row ────────────────────────────────
    op.execute(
        sa.text(
            """
            INSERT INTO scoring_weights (id, velocity_weight, evergreen_weight, fit_weight, saturation_weight, performance_delta, iteration)
            VALUES (gen_random_uuid(), 0.4, 0.3, 0.2, 0.1, 0.0, 1)
            """
        )
    )


def downgrade() -> None:
    # Drop composite indexes
    op.drop_index("ix_analytics_snapshots_snapshot_at", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_variant_platform", table_name="analytics_snapshots")
    op.drop_index("ix_upload_schedule_platform_status", table_name="upload_schedule")
    op.drop_index("ix_platform_variants_platform_status", table_name="platform_variants")
    op.drop_index("ix_content_assets_brief_status", table_name="content_assets")
    op.drop_index("ix_content_briefs_topic_status", table_name="content_briefs")
    op.drop_index("ix_topics_discovered_score", table_name="topics")
    op.drop_index("ix_topics_score_status", table_name="topics")

    # Drop tables in reverse FK order
    op.drop_table("repost_queue")
    op.drop_table("platform_rules")
    op.drop_table("scoring_weights")
    op.drop_table("analytics_snapshots")
    op.drop_table("upload_schedule")
    op.drop_table("platform_variants")
    op.drop_table("content_assets")
    op.drop_table("content_briefs")
    op.drop_table("hooks")
    op.drop_table("topics")

    # Drop enum types
    for enum_name in [
        "schedule_status", "variant_status", "asset_status",
        "asset_stage", "asset_type", "brief_status", "topic_status",
    ]:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
