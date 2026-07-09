"""Topic Pydantic schemas for request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TopicCreate(BaseModel):
    """Schema for manually creating a topic."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    source_apis: list[str] | None = None
    raw_data: dict[str, Any] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    composite_score: float | None = None
    velocity_score: float | None = None
    evergreen_score: float | None = None
    platform_fit: float | None = None
    saturation: float | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class TopicScoreBreakdown(BaseModel):
    """Detailed score breakdown for a topic."""

    composite_score: float
    velocity_score: float
    evergreen_score: float
    platform_fit: float
    saturation: float


class TopicResponse(BaseModel):
    """Full topic response."""

    id: uuid.UUID
    title: str
    description: str | None
    composite_score: float
    velocity_score: float
    evergreen_score: float
    platform_fit: float
    saturation: float
    status: str
    source_apis: list[str] | None
    raw_data: dict[str, Any] | None
    discovered_at: datetime
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicList(BaseModel):
    """Paginated topic list."""

    items: list[TopicResponse]
    total: int
    page: int
    page_size: int
    pages: int
