"""Settings API routes — configuration management and API status checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.analytics import ScoringWeight
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# API keys map: display name -> settings attribute name
_API_KEYS_MAP: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "runway": "RUNWAY_API_KEY",
    "bannerbear": "BANNERBEAR_API_KEY",
    "youtube": "YOUTUBE_API_KEY",
    "twitter": "TWITTER_BEARER_TOKEN",
    "buzzsumo": "BUZZSUMO_API_KEY",
    "serpapi": "SERPAPI_KEY",
    "newsapi": "NEWSAPI_KEY",
    "pexels": "PEXELS_API_KEY",
    "semrush": "SEMRUSH_API_KEY",
    "reddit": "REDDIT_CLIENT_ID",
    "aws": "AWS_ACCESS_KEY_ID",
    "auphonic": "AUPHONIC_API_KEY",
    "linkedin": "LINKEDIN_ACCESS_TOKEN",
    "tiktok": "TIKTOK_ACCESS_TOKEN",
}


@router.get("", response_model=dict)
async def get_settings_values(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return all non-sensitive configuration values."""
    settings = get_settings()

    # Load current scoring weights from DB
    weights_result = await db.execute(
        select(ScoringWeight).order_by(ScoringWeight.updated_at.desc()).limit(1)
    )
    weights = weights_result.scalar_one_or_none()

    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "s3_bucket": settings.S3_BUCKET,
        "aws_region": settings.AWS_REGION,
        "min_score_threshold": settings.MIN_SCORE_THRESHOLD,
        "max_saturation": settings.MAX_SATURATION,
        "scoring_weights": {
            "velocity_weight": weights.velocity_weight if weights else settings.VELOCITY_WEIGHT,
            "evergreen_weight": weights.evergreen_weight if weights else settings.EVERGREEN_WEIGHT,
            "fit_weight": weights.fit_weight if weights else settings.FIT_WEIGHT,
            "saturation_weight": weights.saturation_weight if weights else settings.SATURATION_WEIGHT,
            "iteration": weights.iteration if weights else 1,
        },
        "platforms": ["youtube", "tiktok", "instagram", "twitter", "linkedin"],
    }


@router.put("", response_model=dict)
async def update_settings(
    updates: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update configuration values (scoring weights, posting frequency, etc.)."""
    updated_fields: list[str] = []

    # Handle scoring weights update
    scoring = updates.get("scoring_weights")
    if scoring and isinstance(scoring, dict):
        weights_result = await db.execute(
            select(ScoringWeight).order_by(ScoringWeight.updated_at.desc()).limit(1)
        )
        current_weights = weights_result.scalar_one_or_none()

        if current_weights is None:
            new_weights = ScoringWeight(
                velocity_weight=scoring.get("velocity_weight", 0.4),
                evergreen_weight=scoring.get("evergreen_weight", 0.3),
                fit_weight=scoring.get("fit_weight", 0.2),
                saturation_weight=scoring.get("saturation_weight", 0.1),
                iteration=1,
            )
            db.add(new_weights)
        else:
            if "velocity_weight" in scoring:
                current_weights.velocity_weight = scoring["velocity_weight"]
            if "evergreen_weight" in scoring:
                current_weights.evergreen_weight = scoring["evergreen_weight"]
            if "fit_weight" in scoring:
                current_weights.fit_weight = scoring["fit_weight"]
            if "saturation_weight" in scoring:
                current_weights.saturation_weight = scoring["saturation_weight"]
            current_weights.iteration += 1

        updated_fields.append("scoring_weights")
        await db.flush()

    logger.info("settings_updated", updated_fields=updated_fields)

    return {
        "status": "updated",
        "updated_fields": updated_fields,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api-status", response_model=dict)
async def api_status() -> dict[str, Any]:
    """Check which API keys are configured and return status per API."""
    settings = get_settings()
    statuses: dict[str, dict[str, Any]] = {}

    for api_name, attr_name in _API_KEYS_MAP.items():
        value = getattr(settings, attr_name, "")
        is_configured = bool(value and len(value) > 0)
        statuses[api_name] = {
            "configured": is_configured,
            "key_preview": f"{value[:4]}...{value[-4:]}" if is_configured and len(value) > 8 else ("***" if is_configured else ""),
        }

    total_configured = sum(1 for s in statuses.values() if s["configured"])
    return {
        "apis": statuses,
        "total_configured": total_configured,
        "total_available": len(_API_KEYS_MAP),
    }


@router.post("/test-api/{api_name}", response_model=dict)
async def test_api_connectivity(api_name: str) -> dict[str, Any]:
    """Test connectivity for a specific API by making a simple request."""
    settings = get_settings()

    if api_name not in _API_KEYS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown API '{api_name}'. Available: {list(_API_KEYS_MAP.keys())}",
        )

    attr_name = _API_KEYS_MAP[api_name]
    api_key = getattr(settings, attr_name, "")

    if not api_key:
        return {
            "api": api_name,
            "status": "not_configured",
            "message": f"API key for {api_name} is not set",
        }

    # Test endpoints for supported APIs
    test_results = await _test_api_endpoint(api_name, api_key, settings)
    return test_results


async def _test_api_endpoint(
    api_name: str, api_key: str, settings: Any
) -> dict[str, Any]:
    """Execute a lightweight test request for the specified API."""
    test_configs: dict[str, dict[str, Any]] = {
        "youtube": {
            "url": "https://www.googleapis.com/youtube/v3/videos",
            "params": {"part": "id", "chart": "mostPopular", "maxResults": "1", "key": api_key},
        },
        "newsapi": {
            "url": "https://newsapi.org/v2/top-headlines",
            "params": {"country": "us", "pageSize": "1", "apiKey": api_key},
        },
        "pexels": {
            "url": "https://api.pexels.com/v1/search",
            "params": {"query": "test", "per_page": "1"},
            "headers": {"Authorization": api_key},
        },
        "serpapi": {
            "url": "https://serpapi.com/account",
            "params": {"api_key": api_key},
        },
        "twitter": {
            "url": "https://api.twitter.com/2/tweets/search/recent",
            "params": {"query": "test", "max_results": "10"},
            "headers": {"Authorization": f"Bearer {api_key}"},
        },
    }

    config = test_configs.get(api_name)
    if config is None:
        # For APIs without a simple test endpoint, just verify the key exists
        return {
            "api": api_name,
            "status": "configured",
            "message": f"API key is set. Connectivity test not available for {api_name}.",
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                config["url"],
                params=config.get("params"),
                headers=config.get("headers"),
            )

        is_success = response.status_code in (200, 201)
        return {
            "api": api_name,
            "status": "connected" if is_success else "error",
            "http_status": response.status_code,
            "message": "API is reachable and responding" if is_success else f"API returned status {response.status_code}",
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.TimeoutException:
        return {
            "api": api_name,
            "status": "timeout",
            "message": "API request timed out after 15 seconds",
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "api": api_name,
            "status": "error",
            "message": f"Connection failed: {exc}",
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }
