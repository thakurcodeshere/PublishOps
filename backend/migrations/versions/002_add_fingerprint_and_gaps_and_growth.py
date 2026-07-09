"""Add fingerprint, gaps, arcs, and viral gate tables.

Revision ID: 002_add_fingerprint_and_gaps_and_growth
Revises: 001_initial_schema
Create Date: 2026-06-17

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_fingerprint_and_gaps_and_growth"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Creator Calibration Tables (Tier C) ─────────────────────────────
    op.create_table(
        "creator_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "lexical_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cadence_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "acoustic_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "disfluency_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "temporal_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("profile_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "opinion_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("stance", sa.Text, nullable=False),
        sa.Column("allowed_terms", postgresql.JSONB, nullable=False),
        sa.Column("forbidden_terms", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 2. Competitor Intelligence Tables (Tier A) ──────────────────────────
    op.create_table(
        "competitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("follower_count", sa.Integer, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "competitor_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("url", sa.String(1024), nullable=False, unique=True),
        sa.Column("publish_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views", sa.Integer, nullable=True),
        sa.Column("engagement_rate", sa.Float, nullable=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "coverage_matrices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword_cluster", sa.String(255), nullable=False),
        sa.Column("coverage_score", sa.Float, nullable=False),
        sa.Column("demand_score", sa.Float, nullable=False),
        sa.Column("gap_score", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 3. Audience Vocabulary Mining (Tier A) ─────────────────────────────
    op.create_table(
        "audience_phrases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phrase", sa.Text, nullable=False),
        sa.Column("source_platform", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("frequency", sa.Integer, nullable=False, server_default="1"),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("pain_point_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "vocab_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("phrases", postgresql.JSONB, nullable=False),
        sa.Column("representative_phrase", sa.Text, nullable=False),
        sa.Column("target_persona", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 4. Narrative Campaign Arcs (Tier B) ───────────────────────────────
    op.create_table(
        "content_arcs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_audience", sa.String(255), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "arc_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "arc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_arcs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column("content_brief_ids", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "content_mix_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "arc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_arcs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("educational_pct", sa.Float, nullable=False, server_default="0.40"),
        sa.Column("entertainment_pct", sa.Float, nullable=False, server_default="0.30"),
        sa.Column("personal_story_pct", sa.Float, nullable=False, server_default="0.20"),
        sa.Column("offer_pct", sa.Float, nullable=False, server_default="0.10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 5. Viral Gate Predictions (Tier B) ────────────────────────────────
    op.create_table(
        "viral_score_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ctr_prediction", sa.Float, nullable=False),
        sa.Column("watch_time_prediction", sa.Float, nullable=False),
        sa.Column("engagement_prediction", sa.Float, nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("passed_gate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "viral_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("accuracy_metrics", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 6. Compliance & Likeness Tables (Tier D) ──────────────────────────
    op.create_table(
        "compliance_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("synthetic_media_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("required_labels", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="passed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "consent_ledgers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creator_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consent_given", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_trails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False, server_default="system"),
        sa.Column("details", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 7. Revenue Attribution Tables (Tier E) ─────────────────────────────
    op.create_table(
        "revenue_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", sa.String(255), nullable=False, unique=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "content_revenue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("revenue_attributed", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("conversion_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "attribution_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("utm_code", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_url", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 8. Self-Learning Experiments (Tier F) ──────────────────────────────
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("format_details", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "experiment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_improvement_pct", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("is_winner", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 9. Reliability & Cost Governance (Tier F) ──────────────────────────
    op.create_table(
        "pipeline_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stage", sa.String(100), nullable=False),
        sa.Column("error_msg", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cost_ledgers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("amount_usd", sa.Float, nullable=False),
        sa.Column("billing_period", sa.String(7), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "service_health",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_table("service_health")
    op.drop_table("cost_ledgers")
    op.drop_table("pipeline_incidents")
    op.drop_table("experiment_results")
    op.drop_table("experiments")
    op.drop_table("attribution_links")
    op.drop_table("content_revenue")
    op.drop_table("revenue_events")
    op.drop_table("audit_trails")
    op.drop_table("consent_ledgers")
    op.drop_table("compliance_checks")
    op.drop_table("viral_model_versions")
    op.drop_table("viral_score_results")
    op.drop_table("content_mix_targets")
    op.drop_table("arc_segments")
    op.drop_table("content_arcs")
    op.drop_table("vocab_clusters")
    op.drop_table("audience_phrases")
    op.drop_table("coverage_matrices")
    op.drop_table("competitor_content")
    op.drop_table("competitors")
    op.drop_table("opinion_entries")
    op.drop_table("temporal_profiles")
    op.drop_table("disfluency_profiles")
    op.drop_table("acoustic_profiles")
    op.drop_table("cadence_profiles")
    op.drop_table("lexical_profiles")
    op.drop_table("creator_profiles")
