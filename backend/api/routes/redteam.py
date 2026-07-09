"""Red-Team API routes (Tier C) for adversarial verification and content auditing."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.content import ContentAsset, AssetStatus
from backend.models.creator_profile import CreatorProfile
from backend.services.redteam.red_team import RedTeamOrchestrator

router = APIRouter()
red_team_orchestrator = RedTeamOrchestrator()


class RedTeamTestRequest(BaseModel):
    asset_id: uuid.UUID
    creator_id: uuid.UUID | None = None


class RedTeamResultResponse(BaseModel):
    passed: bool
    composite_score: float
    scores: dict[str, float]
    failing_channels: list[str]


@router.post("/test", response_model=RedTeamResultResponse)
async def test_asset(
    body: RedTeamTestRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Run adversarial AI detection checks on a registered ContentAsset."""
    # 1. Fetch asset
    asset_result = await db.execute(
        select(ContentAsset).where(ContentAsset.id == body.asset_id)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Content asset not found")

    # 2. Fetch creator profile
    creator = None
    if body.creator_id:
        creator_result = await db.execute(
            select(CreatorProfile).where(CreatorProfile.id == body.creator_id)
        )
        creator = creator_result.scalar_one_or_none()

    # 3. Gather text/audio/video content for testing
    text_content = None
    audio_data = None
    video_data = None

    # Retrieve from asset depending on type
    # For scripts, we extract from asset metadata or file
    if asset.asset_type.value == "script":
        text_content = asset.metadata.get("text", "") if asset.metadata else ""
    elif asset.asset_type.value in ["audio_raw", "audio_enhanced"]:
        # If we have local cached file, read it (simulate/mock if not available)
        # S3 URL is stored, but for testing we can mock or read local cache
        # Let's mock a short file if no real file exists
        audio_data = b"MOCK_WAV_AUDIO_DATA"
    elif asset.asset_type.value in ["video_clip", "video_assembled"]:
        video_data = b"MOCK_MP4_VIDEO_DATA"

    # Run tests
    results = await red_team_orchestrator.test_content(
        text_content=text_content,
        audio_data=audio_data,
        video_data=video_data,
        creator_profile=creator
    )

    # 4. Save results back into asset metadata
    if not asset.metadata:
        asset.metadata = {}
    
    asset.metadata["red_team"] = results
    
    # Update status based on test outcome
    if not results["passed"]:
        asset.status = AssetStatus.FAILED
        asset.error_log = f"Failed red-team verification. AI probability: {results['composite_score']}"
    else:
        # If passed and was previously in failed state, restore it
        if asset.status == AssetStatus.FAILED:
            asset.status = AssetStatus.COMPLETED

    db.add(asset)
    await db.commit()

    return results


@router.get("/results/{asset_id}", response_model=RedTeamResultResponse)
async def get_test_results(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve the adversarial test metrics for a content asset."""
    result = await db.execute(select(ContentAsset).where(ContentAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    red_team_data = asset.metadata.get("red_team") if asset.metadata else None
    if not red_team_data:
        raise HTTPException(status_code=404, detail="No red-team results found for this asset")

    return red_team_data


@router.post("/test-raw", response_model=RedTeamResultResponse)
async def test_raw_content(
    text: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    video_file: UploadFile | None = File(None),
    creator_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Test raw content files on the fly without saving to an asset."""
    creator = None
    if creator_id:
        creator_result = await db.execute(select(CreatorProfile).where(CreatorProfile.id == creator_id))
        creator = creator_result.scalar_one_or_none()

    audio_bytes = await audio_file.read() if audio_file else None
    video_bytes = await video_file.read() if video_file else None

    return await red_team_orchestrator.test_content(
        text_content=text,
        audio_data=audio_bytes,
        video_data=video_bytes,
        creator_profile=creator
    )
