"""Content Pydantic schemas — briefs, assets, and variants."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BriefCreate(BaseModel):
    """Schema for creating a content brief."""

    topic_id: uuid.UUID
    hook_id: uuid.UUID | None = None
    format: str = Field(..., min_length=1, max_length=50)
    target_emotion: str = Field(..., min_length=1, max_length=50)
    target_platforms: list[str] | None = None
    talking_points: dict[str, Any] | None = None
    cta_strategy: str | None = None
    variants_planned: int = Field(default=6, ge=1, le=20)
    brief_text: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class BriefResponse(BaseModel):
    """Full content brief response."""

    id: uuid.UUID
    topic_id: uuid.UUID
    hook_id: uuid.UUID | None
    format: str
    target_emotion: str
    target_platforms: list[str] | None
    talking_points: dict[str, Any] | None
    cta_strategy: str | None
    variants_planned: int
    brief_text: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetResponse(BaseModel):
    """Content asset response."""

    id: uuid.UUID
    brief_id: uuid.UUID
    asset_type: str
    s3_key: str | None
    s3_url: str | None
    file_size_bytes: int | None
    duration_secs: float | None
    metadata: dict[str, Any] | None
    stage: str
    status: str
    error_log: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariantResponse(BaseModel):
    """Platform variant response."""

    id: uuid.UUID
    asset_id: uuid.UUID
    brief_id: uuid.UUID
    platform: str
    aspect_ratio: str
    title: str | None
    caption: str | None
    hashtags: list[str] | None
    s3_key: str | None
    specs: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
