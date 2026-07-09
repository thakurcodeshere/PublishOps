"""Pipeline Pydantic schemas — run status and stage tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Stages in the content pipeline."""

    INTELLIGENCE = "intelligence"
    STRATEGY = "strategy"
    CREATION = "creation"
    HUMANIZATION = "humanization"
    OPTIMIZATION = "optimization"
    SCHEDULING = "scheduling"
    ANALYTICS = "analytics"


class StageStatusEnum(str, Enum):
    """Status of a pipeline stage."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageStatus(BaseModel):
    """Status of a single pipeline stage."""

    stage: PipelineStage
    status: StageStatusEnum = StageStatusEnum.IDLE
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    items_processed: int = 0
    items_failed: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineStatus(BaseModel):
    """Current pipeline status across all stages."""

    is_running: bool = False
    current_stage: PipelineStage | None = None
    stages: list[StageStatus] = Field(default_factory=list)
    last_run_at: datetime | None = None
    next_scheduled_run: datetime | None = None


class PipelineRun(BaseModel):
    """Record of a single pipeline execution."""

    id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    trigger: str = "manual"  # manual, scheduled, api
    stages: list[StageStatus] = Field(default_factory=list)
    total_topics_discovered: int = 0
    total_briefs_generated: int = 0
    total_assets_created: int = 0
    total_variants_produced: int = 0
    total_posts_scheduled: int = 0
    status: StageStatusEnum = StageStatusEnum.IDLE
    error_log: str | None = None


class PipelineTriggerRequest(BaseModel):
    """Request body for manually triggering a pipeline run."""

    stages: list[PipelineStage] | None = None  # None = run all
    topic_ids: list[uuid.UUID] | None = None  # Specific topics to process
    force: bool = False  # Skip deduplication and filtering


class PipelineHealthCheck(BaseModel):
    """Health status of all pipeline services."""

    database: bool = False
    redis: bool = False
    anthropic: bool = False
    elevenlabs: bool = False
    s3: bool = False
    scrapers: dict[str, bool] = Field(default_factory=dict)
    overall: bool = False
    checked_at: datetime | None = None
