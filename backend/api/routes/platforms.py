"""Platforms API routes — platform rules, specs, and algorithm signals."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.analytics import PlatformRule
from backend.schemas.analytics import PlatformRuleCreate, PlatformRuleResponse
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Supported platforms
PLATFORMS = ["youtube", "tiktok", "instagram", "twitter", "linkedin"]

# Platform format specifications
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "youtube": {
        "name": "YouTube",
        "video": {
            "aspect_ratios": ["16:9", "9:16"],
            "max_duration_seconds": 43200,  # 12 hours
            "max_file_size_mb": 256000,
            "supported_formats": ["mp4", "mov", "avi", "wmv", "flv", "webm"],
            "recommended_resolution": "1920x1080",
        },
        "thumbnail": {
            "aspect_ratio": "16:9",
            "recommended_size": "1280x720",
            "max_file_size_mb": 2,
            "supported_formats": ["jpg", "png", "gif", "bmp"],
        },
        "title": {"max_length": 100},
        "description": {"max_length": 5000},
        "tags": {"max_count": 500, "max_length_each": 30},
    },
    "tiktok": {
        "name": "TikTok",
        "video": {
            "aspect_ratios": ["9:16", "1:1"],
            "max_duration_seconds": 600,  # 10 minutes
            "max_file_size_mb": 4096,
            "supported_formats": ["mp4", "mov", "webm"],
            "recommended_resolution": "1080x1920",
        },
        "title": {"max_length": 150},
        "description": {"max_length": 4000},
        "hashtags": {"max_count": 30},
    },
    "instagram": {
        "name": "Instagram",
        "video": {
            "aspect_ratios": ["9:16", "1:1", "4:5"],
            "max_duration_seconds": 5400,  # 90 minutes for Reels
            "max_file_size_mb": 4096,
            "supported_formats": ["mp4", "mov"],
            "recommended_resolution": "1080x1920",
        },
        "image": {
            "aspect_ratios": ["1:1", "4:5", "1.91:1"],
            "recommended_size": "1080x1080",
            "max_file_size_mb": 30,
            "supported_formats": ["jpg", "png", "bmp"],
        },
        "caption": {"max_length": 2200},
        "hashtags": {"max_count": 30},
    },
    "twitter": {
        "name": "Twitter / X",
        "video": {
            "aspect_ratios": ["16:9", "1:1"],
            "max_duration_seconds": 140,
            "max_file_size_mb": 512,
            "supported_formats": ["mp4", "mov"],
            "recommended_resolution": "1920x1080",
        },
        "image": {
            "aspect_ratios": ["16:9", "1:1"],
            "max_file_size_mb": 5,
            "supported_formats": ["jpg", "png", "gif", "webp"],
        },
        "tweet": {"max_length": 280},
    },
    "linkedin": {
        "name": "LinkedIn",
        "video": {
            "aspect_ratios": ["16:9", "1:1", "9:16"],
            "max_duration_seconds": 600,
            "max_file_size_mb": 5120,
            "supported_formats": ["mp4", "mov"],
            "recommended_resolution": "1920x1080",
        },
        "image": {
            "aspect_ratios": ["1.91:1", "1:1", "4:5"],
            "max_file_size_mb": 10,
            "supported_formats": ["jpg", "png", "gif"],
        },
        "post": {"max_length": 3000},
        "title": {"max_length": 200},
    },
}


@router.get("", response_model=list[dict])
async def list_platforms(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all supported platforms with their rule counts."""
    results: list[dict[str, Any]] = []

    for platform in PLATFORMS:
        # Count rules for this platform
        from sqlalchemy import func

        count_result = await db.execute(
            select(func.count(PlatformRule.id)).where(
                PlatformRule.platform == platform
            )
        )
        rule_count = count_result.scalar() or 0

        results.append(
            {
                "platform": platform,
                "display_name": PLATFORM_SPECS[platform]["name"],
                "rule_count": rule_count,
                "has_specs": True,
            }
        )

    return results


@router.get("/{platform}/rules", response_model=list[PlatformRuleResponse])
async def get_platform_rules(
    platform: str,
    db: AsyncSession = Depends(get_db),
) -> list[PlatformRuleResponse]:
    """Get algorithm rules and optimization signals for a platform."""
    platform_lower = platform.lower()
    if platform_lower not in PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{platform}'. Available: {PLATFORMS}",
        )

    result = await db.execute(
        select(PlatformRule)
        .where(PlatformRule.platform == platform_lower)
        .order_by(PlatformRule.signal_weight.desc())
    )
    rules = list(result.scalars().all())

    return [PlatformRuleResponse.model_validate(r) for r in rules]


@router.put("/{platform}/rules", response_model=list[PlatformRuleResponse])
async def update_platform_rules(
    platform: str,
    rules: list[PlatformRuleCreate],
    db: AsyncSession = Depends(get_db),
) -> list[PlatformRuleResponse]:
    """Update algorithm rules for a platform (replace all rules)."""
    platform_lower = platform.lower()
    if platform_lower not in PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{platform}'. Available: {PLATFORMS}",
        )

    # Delete existing rules for this platform
    existing_result = await db.execute(
        select(PlatformRule).where(PlatformRule.platform == platform_lower)
    )
    existing_rules = list(existing_result.scalars().all())
    for rule in existing_rules:
        await db.delete(rule)
    await db.flush()

    # Insert new rules
    new_rules: list[PlatformRule] = []
    for rule_data in rules:
        new_rule = PlatformRule(
            platform=platform_lower,
            signal_name=rule_data.signal_name,
            signal_weight=rule_data.signal_weight,
            description=rule_data.description,
            optimization_notes=rule_data.optimization_notes,
        )
        db.add(new_rule)
        new_rules.append(new_rule)

    await db.flush()

    logger.info(
        "platform_rules_updated",
        platform=platform_lower,
        rule_count=len(new_rules),
    )

    return [PlatformRuleResponse.model_validate(r) for r in new_rules]


@router.get("/{platform}/specs", response_model=dict)
async def get_platform_specs(
    platform: str,
) -> dict[str, Any]:
    """Get format specifications for a platform."""
    platform_lower = platform.lower()
    if platform_lower not in PLATFORM_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{platform}'. Available: {PLATFORMS}",
        )

    return {
        "platform": platform_lower,
        "specs": PLATFORM_SPECS[platform_lower],
    }
