"""Content API routes — briefs, assets, variants, and regeneration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.content import (
    AssetStage,
    AssetStatus,
    AssetType,
    BriefStatus,
    ContentAsset,
    ContentBrief,
)
from backend.models.platform_variant import PlatformVariant
from backend.schemas.content import AssetResponse, BriefResponse, VariantResponse
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)

router = APIRouter()


@router.get("/briefs", response_model=dict)
async def list_briefs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by brief status"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List content briefs with pagination and optional status filter."""
    query = select(ContentBrief)

    if status is not None:
        try:
            status_enum = BriefStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {[s.value for s in BriefStatus]}",
            )
        query = query.where(ContentBrief.status == status_enum)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ContentBrief.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    briefs = list(result.scalars().all())

    page = (skip // limit) + 1 if limit > 0 else 1
    pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1

    return {
        "items": [BriefResponse.model_validate(b) for b in briefs],
        "total": total,
        "page": page,
        "page_size": limit,
        "pages": pages,
    }


@router.get("/briefs/{brief_id}", response_model=dict)
async def get_brief(
    brief_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a content brief with related assets and variants."""
    result = await db.execute(
        select(ContentBrief)
        .options(selectinload(ContentBrief.assets), selectinload(ContentBrief.variants))
        .where(ContentBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()

    if brief is None:
        raise HTTPException(status_code=404, detail=f"Brief {brief_id} not found")

    return {
        "brief": BriefResponse.model_validate(brief),
        "assets": [AssetResponse.model_validate(a) for a in brief.assets],
        "variants": [VariantResponse.model_validate(v) for v in brief.variants],
    }


@router.get("/assets", response_model=dict)
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    asset_type: str | None = Query(None, description="Filter by asset type"),
    status: str | None = Query(None, description="Filter by asset status"),
    stage: str | None = Query(None, description="Filter by asset stage"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List content assets with optional filters."""
    query = select(ContentAsset)

    if asset_type is not None:
        try:
            type_enum = AssetType(asset_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid asset_type '{asset_type}'. Valid: {[t.value for t in AssetType]}",
            )
        query = query.where(ContentAsset.asset_type == type_enum)

    if status is not None:
        try:
            status_enum = AssetStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {[s.value for s in AssetStatus]}",
            )
        query = query.where(ContentAsset.status == status_enum)

    if stage is not None:
        try:
            stage_enum = AssetStage(stage)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{stage}'. Valid: {[s.value for s in AssetStage]}",
            )
        query = query.where(ContentAsset.stage == stage_enum)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ContentAsset.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    assets = list(result.scalars().all())

    page = (skip // limit) + 1 if limit > 0 else 1
    pages = max(1, (total + limit - 1) // limit) if limit > 0 else 1

    return {
        "items": [AssetResponse.model_validate(a) for a in assets],
        "total": total,
        "page": page,
        "page_size": limit,
        "pages": pages,
    }


@router.get("/assets/{asset_id}", response_model=dict)
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get an asset with a pre-signed S3 download URL."""
    result = await db.execute(
        select(ContentAsset).where(ContentAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    presigned_url: str | None = None
    if asset.s3_key:
        try:
            s3 = S3Client()
            presigned_url = await s3.generate_presigned_url(asset.s3_key, expiration=3600)
        except Exception as exc:
            logger.warning(
                "presigned_url_generation_failed",
                asset_id=str(asset_id),
                error=str(exc),
            )

    return {
        "asset": AssetResponse.model_validate(asset),
        "presigned_url": presigned_url,
    }


@router.get("/variants", response_model=list[VariantResponse])
async def list_variants(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    platform: str | None = Query(None, description="Filter by platform"),
    db: AsyncSession = Depends(get_db),
) -> list[VariantResponse]:
    """List platform variants with optional platform filter."""
    query = select(PlatformVariant)

    if platform is not None:
        query = query.where(PlatformVariant.platform == platform.lower())

    query = query.order_by(PlatformVariant.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    variants = list(result.scalars().all())

    return [VariantResponse.model_validate(v) for v in variants]


@router.post("/regenerate/{asset_id}", response_model=dict)
async def regenerate_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-trigger content creation for a failed or completed asset."""
    result = await db.execute(
        select(ContentAsset).where(ContentAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    if asset.status == AssetStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail="Asset is currently being processed. Wait for completion before regenerating.",
        )

    # Reset asset status to trigger re-processing
    asset.status = AssetStatus.PENDING
    asset.error_log = None
    await db.flush()

    logger.info(
        "asset_regeneration_triggered",
        asset_id=str(asset_id),
        asset_type=asset.asset_type.value,
        stage=asset.stage.value,
    )

    return {
        "message": "Asset regeneration triggered",
        "asset_id": str(asset_id),
        "new_status": asset.status.value,
    }
