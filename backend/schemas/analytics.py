"""Analytics Pydantic schemas — snapshots, weights, rules, dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsSnapshotResponse(BaseModel):
    """Analytics snapshot response."""

    id: uuid.UUID
    variant_id: uuid.UUID
    platform: str
    days_since_post: int
    metrics: dict[str, Any]
    snapshot_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoringWeightsResponse(BaseModel):
    """Scoring weights response."""

    id: uuid.UUID
    velocity_weight: float
    evergreen_weight: float
    fit_weight: float
    saturation_weight: float
    performance_delta: float | None
    iteration: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoringWeightsUpdate(BaseModel):
    """Schema for updating scoring weights."""

    velocity_weight: float = Field(ge=0.0, le=1.0)
    evergreen_weight: float = Field(ge=0.0, le=1.0)
    fit_weight: float = Field(ge=0.0, le=1.0)
    saturation_weight: float = Field(ge=0.0, le=1.0)


class PlatformRuleCreate(BaseModel):
    """Schema for creating a platform rule."""

    platform: str = Field(..., min_length=1, max_length=50)
    signal_name: str = Field(..., min_length=1, max_length=200)
    signal_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    description: str | None = None
    optimization_notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class PlatformRuleResponse(BaseModel):
    """Platform rule response."""

    id: uuid.UUID
    platform: str
    signal_name: str
    signal_weight: float
    description: str | None
    optimization_notes: str | None
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformMetrics(BaseModel):
    """Aggregated metrics for a single platform."""

    platform: str
    total_posts: int = 0
    total_views: int = 0
    total_engagement: int = 0
    avg_ctr: float = 0.0
    avg_watch_time: float = 0.0
    top_performer_id: uuid.UUID | None = None


class DashboardStats(BaseModel):
    """Aggregated dashboard statistics."""

    total_topics_discovered: int = 0
    total_topics_accepted: int = 0
    total_briefs: int = 0
    total_assets: int = 0
    total_variants: int = 0
    total_posts_scheduled: int = 0
    total_posts_published: int = 0
    avg_composite_score: float = 0.0
    platform_metrics: list[PlatformMetrics] = Field(default_factory=list)
    score_distribution: dict[str, int] = Field(default_factory=dict)
    recent_performance_delta: float = 0.0


class TrendPoint(BaseModel):
    """A single data point in a trend time series."""

    date: datetime
    value: float
    label: str | None = None


class MetricTrend(BaseModel):
    """Trend data for a specific metric."""

    metric_name: str
    data_points: list[TrendPoint] = Field(default_factory=list)
    total_change_pct: float = 0.0
