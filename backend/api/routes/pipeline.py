"""Pipeline API routes — status, runs, triggers, health checks, and DAG pipeline stages."""

from __future__ import annotations

import os
import uuid
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.schemas.pipeline import (
    PipelineHealthCheck,
    PipelineRun,
    PipelineStage,
    PipelineStatus,
    PipelineTriggerRequest,
    StageStatus,
    StageStatusEnum,
)

# Model imports
from backend.models.topic import Topic, TopicStatus
from backend.models.content import ContentBrief, ContentAsset, BriefStatus, AssetType, AssetStatus, AssetStage
from backend.models.platform_variant import PlatformVariant, VariantStatus
from backend.models.schedule import UploadSchedule, ScheduleStatus
from backend.models.creator_profile import CreatorProfile
from backend.models.governance import PipelineIncident

# Service imports
from backend.services.intelligence.engine import IntelligenceEngine
from backend.services.intelligence.scorer import TopicScorer, RawTopic
from backend.services.strategy.brief_generator import BriefGenerator
from backend.services.creation.pipeline import CreationPipeline
from backend.services.creation.viral_gate import ViralScoreGate
from backend.services.humanization.script_humanizer import ScriptHumanizer
from backend.services.redteam.red_team import RedTeamOrchestrator
from backend.services.optimizer.repackager import MasterRepackager
from backend.services.distribution.compliance_gate import ComplianceGate
from backend.services.distribution.synergy_router import SynergyRouter
from backend.services.scheduler.window_calculator import WindowCalculator
from backend.services.learning.model_evolution import ModelEvolutionService
from backend.services.learning.governance import GovernanceService

from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)

router = APIRouter()

SCRAPER_NAMES = [
    "google_trends",
    "reddit",
    "youtube",
    "tiktok",
    "buzzsumo",
    "twitter",
    "newsapi",
    "serpapi",
    "semrush",
    "pexels",
]


# ── Existing Endpoints ───────────────────────────────────────────────────

@router.get("/status", response_model=PipelineStatus)
async def pipeline_status() -> PipelineStatus:
    """Return current pipeline stage statuses."""
    stages = [
        StageStatus(stage=stage, status=StageStatusEnum.IDLE)
        for stage in PipelineStage
    ]

    return PipelineStatus(
        is_running=False,
        current_stage=None,
        stages=stages,
        last_run_at=None,
        next_scheduled_run=None,
    )


@router.get("/runs", response_model=list[PipelineRun])
async def list_pipeline_runs(
    limit: int = 10,
) -> list[PipelineRun]:
    """List recent pipeline runs."""
    return []


@router.post("/trigger", response_model=dict)
async def trigger_pipeline(
    body: PipelineTriggerRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually trigger a full pipeline run through the intelligence engine."""
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)

    logger.info(
        "pipeline_trigger_manual",
        run_id=str(run_id),
        stages=[s.value for s in (body.stages if body and body.stages else [])],
        force=body.force if body else False,
    )

    engine = IntelligenceEngine(session=db)
    try:
        scored_topics = await engine.run()
        status = StageStatusEnum.COMPLETED
        error_log = None
    except Exception as exc:
        logger.error("pipeline_run_failed", run_id=str(run_id), error=str(exc))
        scored_topics = []
        status = StageStatusEnum.FAILED
        error_log = str(exc)
    finally:
        await engine.close()

    completed_at = datetime.now(timezone.utc)

    return {
        "run_id": str(run_id),
        "status": status.value,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "topics_discovered": len(scored_topics),
        "error_log": error_log,
    }


@router.post("/trigger-scraper/{scraper_name}", response_model=dict)
async def trigger_scraper(
    scraper_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an individual scraper by name (called by Airflow)."""
    if scraper_name not in SCRAPER_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scraper '{scraper_name}'. Available: {SCRAPER_NAMES}",
        )

    engine = IntelligenceEngine(session=db)
    target_scraper = None
    for scraper in engine.scrapers:
        if scraper.source_name == scraper_name:
            target_scraper = scraper
            break

    if target_scraper is None:
        await engine.close()
        raise HTTPException(
            status_code=404,
            detail=f"Scraper '{scraper_name}' not found in engine",
        )

    try:
        raw_topics = await target_scraper.scrape()
        result_count = len(raw_topics)
        error = None
    except Exception as exc:
        logger.error(
            "scraper_trigger_failed",
            scraper=scraper_name,
            error=str(exc),
        )
        raw_topics = []
        result_count = 0
        error = str(exc)
    finally:
        await engine.close()

    logger.info(
        "scraper_triggered",
        scraper=scraper_name,
        topics_found=result_count,
    )

    return {
        "scraper": scraper_name,
        "topics_found": result_count,
        "error": error,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health", response_model=PipelineHealthCheck)
async def pipeline_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PipelineHealthCheck:
    """Run health checks on all pipeline dependencies."""
    settings = get_settings()
    health = PipelineHealthCheck(checked_at=datetime.now(timezone.utc))

    try:
        await db.execute(text("SELECT 1"))
        health.database = True
    except Exception:
        health.database = False

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        try:
            await redis_client.ping()
            health.redis = True
        except Exception:
            health.redis = False
    else:
        health.redis = False

    health.anthropic = bool(settings.ANTHROPIC_API_KEY)
    health.elevenlabs = bool(settings.ELEVENLABS_API_KEY)

    try:
        s3 = S3Client()
        await s3.list_files(prefix="__health_check__", max_keys=1)
        health.s3 = True
    except Exception:
        health.s3 = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)

    engine = IntelligenceEngine()
    try:
        health.scrapers = await engine.health_check()
    except Exception:
        health.scrapers = {}
    finally:
        await engine.close()

    health.overall = health.database and health.redis

    return health


# ── New Airflow Stage Endpoints ──────────────────────────────────────────

@router.post("/intelligence", response_model=dict)
async def stage_intelligence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 1: Gather trends. Run scrapers and save raw topics as DISCOVERED."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("intelligence")
    passed_budget = await gov.check_budget_gate()
    if not passed_budget:
        raise HTTPException(status_code=400, detail="Pipeline halted: Budget limit exceeded")

    engine = IntelligenceEngine(session=db)
    discovered_topics = []
    try:
        # Fetch raw topics concurrently by running each scraper
        tasks = [scraper.scrape() for scraper in engine.scrapers]
        import asyncio
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        raw_topics = []
        for scraper, result in zip(engine.scrapers, results, strict=False):
            if not isinstance(result, Exception) and isinstance(result, list):
                raw_topics.extend(result)
                
        deduplicated = engine._deduplicate(raw_topics)
        
        # Save into the topics database
        for rt in deduplicated:
            query = select(Topic).where(Topic.title == rt.title)
            check = await db.execute(query)
            existing = check.scalar_one_or_none()
            if not existing:
                topic = Topic(
                    title=rt.title,
                    description=rt.description,
                    status=TopicStatus.DISCOVERED,
                    source_apis=[rt.source],
                    raw_data={
                        "engagement_metrics": rt.engagement_metrics,
                        "raw_data": rt.raw_data,
                        "platform": rt.platform,
                    }
                )
                db.add(topic)
                discovered_topics.append(topic)
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_intelligence_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Intelligence stage error: {exc}")
    finally:
        await engine.close()
        
    return {
        "status": "completed",
        "trends_count": len(discovered_topics),
        "topics": [
            {
                "title": t.title,
                "description": t.description,
                "source": t.source_apis[0] if t.source_apis else "unknown",
                "engagement_metrics": t.raw_data.get("engagement_metrics") if t.raw_data else {},
                "platform": t.raw_data.get("platform") if t.raw_data else "unknown",
                "raw_data": t.raw_data.get("raw_data") if t.raw_data else {}
            }
            for t in discovered_topics
        ]
    }


class ScoreTrendsRequest(BaseModel):
    topics: list[dict[str, Any]]


@router.post("/score-trends", response_model=dict)
async def stage_score_trends(body: ScoreTrendsRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 1b: Score trends. Calculate composite metrics and save scored topics."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("score-trends")

    scorer = TopicScorer(session=db)
    await scorer.load_weights_from_db()
    
    scored_items = []
    
    try:
        # Load all DISCOVERED topics from DB or process the body items
        for item in body.topics:
            raw_topic = RawTopic(
                title=item["title"],
                description=item["description"] or "",
                platform=item.get("platform", "unknown"),
                source=item.get("source", "unknown"),
                engagement_metrics=item.get("engagement_metrics") or {},
                raw_data=item.get("raw_data") or {}
            )
            scored = scorer.score_topic(raw_topic)
            
            # Find in DB and update scores
            query = select(Topic).where(Topic.title == raw_topic.title)
            res = await db.execute(query)
            topic = res.scalar_one_or_none()
            
            if topic:
                topic.composite_score = scored.composite_score
                topic.velocity_score = scored.velocity_score
                topic.evergreen_score = scored.evergreen_score
                topic.platform_fit = scored.platform_fit
                topic.saturation = scored.saturation
                topic.status = TopicStatus.SCORED
                scored_items.append(topic)
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_score_trends_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Score trends stage error: {exc}")
        
    return {
        "status": "completed",
        "scored_count": len(scored_items),
        "topics": [
            {
                "id": str(t.id),
                "title": t.title,
                "composite_score": t.composite_score,
                "velocity_score": t.velocity_score,
                "evergreen_score": t.evergreen_score,
                "platform_fit": t.platform_fit,
                "saturation": t.saturation
            }
            for t in scored_items
        ]
    }


class StrategyRequest(BaseModel):
    topics: list[dict[str, Any]]


@router.post("/strategy", response_model=dict)
async def stage_strategy(body: StrategyRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 2: Generate brief/strategy. Create content briefs for scored topics above threshold."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("strategy")

    bg = BriefGenerator()
    briefs_created = []
    
    try:
        # Filter topics above 65 composite score
        for item in body.topics:
            topic_id = uuid.UUID(item["id"])
            query = select(Topic).where(Topic.id == topic_id)
            res = await db.execute(query)
            topic = res.scalar_one_or_none()
            
            if topic and topic.composite_score >= 65.0:
                # Mock scored topic structure for brief generator
                from backend.services.intelligence.scrapers.base import RawTopic
                from backend.services.intelligence.scorer import ScoredTopic
                
                rt = RawTopic(
                    title=topic.title,
                    description=topic.description or "",
                    platform=topic.raw_data.get("platform") if topic.raw_data else "unknown",
                    source=topic.source_apis[0] if topic.source_apis else "unknown",
                    engagement_metrics=topic.raw_data.get("engagement_metrics") if topic.raw_data else {},
                )
                scored = ScoredTopic(
                    raw=rt,
                    composite_score=topic.composite_score,
                    velocity_score=topic.velocity_score,
                    evergreen_score=topic.evergreen_score,
                    platform_fit=topic.platform_fit,
                    saturation=topic.saturation
                )
                
                brief_data = await bg.generate_brief(scored)
                
                # Save brief in DB
                brief = ContentBrief(
                    topic_id=topic.id,
                    format=brief_data.format,
                    target_emotion=brief_data.target_emotion,
                    target_platforms=[v.get("platform", "youtube") for v in brief_data.platform_variants],
                    talking_points={"points": brief_data.talking_points},
                    cta_strategy=brief_data.cta_strategy,
                    brief_text=brief_data.brief_text,
                    status=BriefStatus.APPROVED
                )
                db.add(brief)
                briefs_created.append(brief)
                
                topic.status = TopicStatus.BRIEF_CREATED
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_strategy_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Strategy stage error: {exc}")
        
    return {
        "status": "completed",
        "items_count": len(briefs_created),
        "briefs": [
            {
                "id": str(b.id),
                "topic_id": str(b.topic_id),
                "format": b.format,
                "target_emotion": b.target_emotion,
                "target_platforms": b.target_platforms
            }
            for b in briefs_created
        ]
    }


class CreateContentRequest(BaseModel):
    briefs: list[dict[str, Any]]


@router.post("/create", response_model=dict)
async def stage_create(body: CreateContentRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 3: Creation. Run scripts, voice synth, clips and thumbnail generation."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("create")

    pipeline = CreationPipeline(session=db)
    assets_created = []
    
    # We fetch a creator profile for calibration/RAG injection
    creator_query = await db.execute(select(CreatorProfile).limit(1))
    creator = creator_query.scalar_one_or_none()
    creator_id = creator.id if creator else None
    
    try:
        for item in body.briefs:
            brief_id = uuid.UUID(item["id"])
            query = select(ContentBrief).where(ContentBrief.id == brief_id)
            res = await db.execute(query)
            brief = res.scalar_one_or_none()
            
            if brief:
                brief.status = BriefStatus.IN_PRODUCTION
                await db.commit()
                
                # Reconstruct BriefData
                from backend.services.strategy.brief_generator import ContentBrief as BriefData
                bd = BriefData(
                    topic_title=brief.topic.title,
                    angle=brief.brief_text or "",
                    talking_points=brief.talking_points.get("points") if brief.talking_points else [],
                    cta_strategy=brief.cta_strategy or "",
                    tone_notes="",
                    target_emotion=brief.target_emotion,
                    format=brief.format
                )
                
                # Run creation pipeline (covers Script -> Viral Gate -> Voice -> Audio Enhance -> Video -> Assembly -> Thumbnail)
                # It handles Viral Score Gate retries internally in creation/pipeline.py
                assets = await pipeline.run(brief, bd, platform=brief.target_platforms[0] if brief.target_platforms else "youtube", creator_id=creator_id)
                assets_created.extend(assets)
                
                brief.status = BriefStatus.COMPLETED
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_create_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Create stage error: {exc}")
        
    return {
        "status": "completed",
        "created_count": len(assets_created),
        "assets": [
            {
                "id": str(a.id),
                "brief_id": str(a.brief_id),
                "asset_type": a.asset_type.value,
                "s3_key": a.s3_key,
                "stage": a.stage.value,
                "status": a.status.value
            }
            for a in assets_created
        ]
    }


class HumanizeRequest(BaseModel):
    assets: list[dict[str, Any]]


@router.post("/humanize", response_model=dict)
async def stage_humanize(body: HumanizeRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 4: Humanization. Apply script conversational humanizer and run Red-Team detector."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("humanize")

    humanizer = ScriptHumanizer()
    redteam = RedTeamOrchestrator()
    s3 = S3Client()
    
    humanized_assets = []
    composite_ai_prob = 0.0
    passed_all = True
    
    try:
        # Check active creator profile if any
        creator_query = await db.execute(select(CreatorProfile).limit(1))
        creator = creator_query.scalar_one_or_none()
        
        for item in body.assets:
            asset_id = uuid.UUID(item["id"])
            query = select(ContentAsset).where(ContentAsset.id == asset_id)
            res = await db.execute(query)
            asset = res.scalar_one_or_none()
            
            if asset and asset.asset_type == AssetType.SCRIPT and asset.s3_key:
                # Read script from S3
                script_bytes = await s3.download_file(asset.s3_key)
                script_data = json.loads(script_bytes.decode())
                
                text_to_humanize = script_data.get("variant_a", {}).get("body", "")
                target_emotion = asset.brief.target_emotion if asset.brief else "curiosity"
                
                # Conversational second-pass
                humanized_text = await humanizer.humanize_script(text_to_humanize, target_emotion)
                script_data["variant_a"]["body"] = humanized_text
                
                # Write back to S3
                updated_bytes = json.dumps(script_data).encode()
                await s3.upload_file(updated_bytes, asset.s3_key, "application/json")
                
                # Run Red-Team Adversarial Gate check
                full_script = f"{script_data['variant_a'].get('hook', '')}\n{humanized_text}\n{script_data['variant_a'].get('cta', '')}"
                rt_results = await redteam.test_content(text_content=full_script, creator_profile=creator)
                
                composite_ai_prob = max(composite_ai_prob, rt_results["composite_score"])
                passed_all = passed_all and rt_results["passed"]
                
                asset.stage = AssetStage.COMPLETE
                humanized_assets.append(asset)
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_humanize_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Humanization stage error: {exc}")
        
    return {
        "status": "completed",
        "ai_detection_score": composite_ai_prob,
        "passed": passed_all,
        "humanized": [
            {
                "id": str(a.id),
                "brief_id": str(a.brief_id),
                "s3_key": a.s3_key,
                "stage": a.stage.value
            }
            for a in humanized_assets
        ]
    }


class OptimizeRequest(BaseModel):
    humanized: list[dict[str, Any]]


@router.post("/optimize", response_model=dict)
async def stage_optimize(body: OptimizeRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 5: Optimization. Repackage for platform-specific specs."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("optimize")

    repackager = MasterRepackager(session=db)
    s3 = S3Client()
    variants_created = []
    
    try:
        for item in body.humanized:
            asset_id = uuid.UUID(item["id"])
            query = select(ContentAsset).where(ContentAsset.id == asset_id)
            res = await db.execute(query)
            asset = res.scalar_one_or_none()
            
            if asset and asset.brief:
                # Load script text
                script_text = ""
                script_asset_query = await db.execute(
                    select(ContentAsset).where(ContentAsset.brief_id == asset.brief_id, ContentAsset.asset_type == AssetType.SCRIPT)
                )
                script_asset = script_asset_query.scalar_one_or_none()
                if script_asset and script_asset.s3_key:
                    script_bytes = await s3.download_file(script_asset.s3_key)
                    script_data = json.loads(script_bytes.decode())
                    script_text = script_data.get("variant_a", {}).get("body", "")
                
                platforms = asset.brief.target_platforms or ["youtube", "tiktok", "instagram", "twitter", "linkedin", "pinterest"]
                
                # Generate platform variants
                variants = await repackager.repackage(
                    content_asset=asset,
                    target_platforms=platforms,
                    title=asset.brief.topic.title,
                    hook_text=asset.brief.topic.title,
                    talking_points=asset.brief.talking_points.get("points") if asset.brief.talking_points else [],
                    script_text=script_text
                )
                variants_created.extend(variants)
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_optimize_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Optimize stage error: {exc}")
        
    return {
        "status": "completed",
        "platforms_count": len(variants_created),
        "variants": [
            {
                "id": str(v.id),
                "platform": v.platform,
                "aspect_ratio": v.aspect_ratio,
                "title": v.title,
                "status": v.status.value
            }
            for v in variants_created
        ]
    }


class ScheduleRequest(BaseModel):
    variants: list[dict[str, Any]]


@router.post("/schedule", response_model=dict)
async def stage_schedule(body: ScheduleRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Stage 6: Scheduling. Compute optimal posting time windows with temporal profile jitter."""
    gov = GovernanceService(session=db)
    await gov.verify_pipeline_safety("schedule")

    wc = WindowCalculator()
    schedules_created = []
    
    creator_query = await db.execute(select(CreatorProfile).limit(1))
    creator = creator_query.scalar_one_or_none()
    creator_id = creator.id if creator else None
    
    try:
        for item in body.variants:
            variant_id = uuid.UUID(item["id"])
            query = select(PlatformVariant).where(PlatformVariant.id == variant_id)
            res = await db.execute(query)
            variant = res.scalar_one_or_none()
            
            if variant:
                # Find existing scheduled times to apply gap rules
                existing_res = await db.execute(
                    select(UploadSchedule.scheduled_at).where(UploadSchedule.platform == variant.platform)
                )
                existing = list(existing_res.scalars().all())
                
                next_time = await wc.get_next_optimal_time(
                    platform=variant.platform,
                    existing_posts=existing,
                    db=db,
                    creator_id=creator_id
                )
                
                if not next_time:
                    next_time = datetime.now(timezone.utc) + timedelta(hours=6)
                
                schedule = UploadSchedule(
                    variant_id=variant.id,
                    platform=variant.platform,
                    scheduled_at=next_time,
                    status=ScheduleStatus.SCHEDULED
                )
                db.add(schedule)
                schedules_created.append(schedule)
                
                variant.status = VariantStatus.READY
                
        await db.commit()
    except Exception as exc:
        logger.error("stage_schedule_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Schedule stage error: {exc}")
        
    return {
        "status": "completed",
        "scheduled_count": len(schedules_created),
        "platforms": len(set(s.platform for s in schedules_created))
    }


# ── Checkpoint Routes ────────────────────────────────────────────────────

class CheckpointRequest(BaseModel):
    brief_id: uuid.UUID


@router.post("/viral-gate", response_model=dict)
async def checkpoint_viral_gate(body: CheckpointRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Viral Score Gate checkpoint (after script creation)."""
    gate = ViralScoreGate()
    
    # Fetch script asset for the brief
    query = select(ContentAsset).where(ContentAsset.brief_id == body.brief_id, ContentAsset.asset_type == AssetType.SCRIPT)
    res = await db.execute(query)
    asset = res.scalar_one_or_none()
    
    if not asset or not asset.s3_key:
        raise HTTPException(status_code=404, detail="Script asset not found for brief")
        
    s3 = S3Client()
    script_bytes = await s3.download_file(asset.s3_key)
    script_data = json.loads(script_bytes.decode())
    full_script = f"{script_data.get('variant_a', {}).get('hook', '')}\n{script_data.get('variant_a', {}).get('body', '')}"
    
    score_result = await gate.predict_virality(db, body.brief_id, full_script)
    return {
        "brief_id": str(body.brief_id),
        "composite_score": score_result.composite_score,
        "passed": score_result.passed_gate,
        "ctr": score_result.ctr_prediction,
        "retention": score_result.watch_time_prediction,
        "engagement": score_result.engagement_prediction
    }


class RedteamCheckpointRequest(BaseModel):
    asset_id: uuid.UUID


@router.post("/redteam", response_model=dict)
async def checkpoint_redteam(body: RedteamCheckpointRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Red-Team adversarial check checkpoint (after humanization)."""
    redteam = RedTeamOrchestrator()
    s3 = S3Client()
    
    query = select(ContentAsset).where(ContentAsset.id == body.asset_id)
    res = await db.execute(query)
    asset = res.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    creator_query = await db.execute(select(CreatorProfile).limit(1))
    creator = creator_query.scalar_one_or_none()
    
    text_content = ""
    audio_data = None
    
    if asset.asset_type == AssetType.SCRIPT and asset.s3_key:
        script_bytes = await s3.download_file(asset.s3_key)
        script_data = json.loads(script_bytes.decode())
        text_content = f"{script_data.get('variant_a', {}).get('hook', '')}\n{script_data.get('variant_a', {}).get('body', '')}"
    
    # Query for associated audio if exists
    audio_query = await db.execute(
        select(ContentAsset).where(ContentAsset.brief_id == asset.brief_id, ContentAsset.asset_type == AssetType.AUDIO_ENHANCED)
    )
    audio_asset = audio_query.scalar_one_or_none()
    if audio_asset and audio_asset.s3_key:
        audio_data = await s3.download_file(audio_asset.s3_key)
        
    rt_results = await redteam.test_content(
        text_content=text_content,
        audio_data=audio_data,
        creator_profile=creator
    )
    
    return {
        "asset_id": str(body.asset_id),
        "passed": rt_results["passed"],
        "composite_score": rt_results["composite_score"],
        "scores": rt_results["scores"],
        "failing_channels": rt_results["failing_channels"]
    }


class ComplianceCheckpointRequest(BaseModel):
    brief_id: uuid.UUID
    platforms: list[str]


@router.post("/compliance", response_model=dict)
async def checkpoint_compliance(body: ComplianceCheckpointRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Compliance Disclosure Gate checkpoint (after optimizer)."""
    gate = ComplianceGate()
    
    creator_query = await db.execute(select(CreatorProfile).limit(1))
    creator = creator_query.scalar_one_or_none()
    if not creator:
        raise HTTPException(status_code=404, detail="No calibrated creator profile found for consent log")
        
    check = await gate.run_prepublish_audit(db, body.brief_id, creator.id, body.platforms)
    return {
        "brief_id": str(body.brief_id),
        "synthetic_media": check.synthetic_media_flag,
        "required_labels": check.required_labels,
        "status": check.status
    }


class SynergyCheckpointRequest(BaseModel):
    platform: str
    destination_url: str
    base_cta_text: str = ""


@router.post("/synergy-routing", response_model=dict)
async def checkpoint_synergy_routing(body: SynergyCheckpointRequest) -> dict[str, Any]:
    """Synergy Router cross-platform native CTA mapping checkpoint (after scheduling)."""
    router_service = SynergyRouter()
    cta = router_service.route_cta_by_platform(body.platform, body.destination_url, body.base_cta_text)
    return {
        "platform": body.platform,
        "destination_url": body.destination_url,
        "cta_text": cta
    }


class EvolveRequest(BaseModel):
    creator_id: uuid.UUID


@router.post("/evolve", response_model=dict)
async def trigger_model_evolution(body: EvolveRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Trigger the self-learning model evolution cycle (RAG, Viral Gate XGBoost retraining, A/B experiments)."""
    evolution_service = ModelEvolutionService(session=db)
    results = await evolution_service.evolve_models(body.creator_id)
    return {
        "status": "success",
        "results": results
    }


@router.post("/governance/health", response_model=dict)
async def trigger_governance_health(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Trigger active latency and ping checking of external APIs."""
    gov = GovernanceService(session=db)
    results = await gov.run_health_checks()
    return {
        "status": "success",
        "checks": results
    }


@router.get("/governance/incidents", response_model=dict)
async def list_active_incidents(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """List all active, unresolved pipeline block incidents."""
    query = select(PipelineIncident).where(PipelineIncident.status == "active")
    res = await db.execute(query)
    incidents = list(res.scalars().all())
    return {
        "active_incidents_count": len(incidents),
        "incidents": [
            {
                "id": str(i.id),
                "stage": i.stage,
                "error_msg": i.error_msg,
                "created_at": i.created_at.isoformat() if i.created_at else None
            }
            for i in incidents
        ]
    }


@router.post("/governance/resolve/{incident_id}", response_model=dict)
async def resolve_pipeline_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Resolve an active pipeline incident to resume operations."""
    gov = GovernanceService(session=db)
    result = await gov.resolve_incident(incident_id)
    return result


@router.post("/seasonal", response_model=dict)
async def trigger_seasonal_planning(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Trigger the seasonal calendar content generation stage. Seeds events if missing, checks lookahead window, and creates briefs."""
    from backend.services.growth.seasonal_calendar import SeasonalCalendar
    from backend.models.seasonal_event import SeasonalEvent
    
    sc = SeasonalCalendar()
    # Check if database has any seasonal events, seed if empty
    check = await db.execute(select(SeasonalEvent).limit(1))
    if not check.scalar_one_or_none():
        seed_path = os.path.join("data", "seasonal_events_seed.json")
        await sc.seed_events(db, seed_file_path=seed_path)
        
    upcoming_unplanned = await sc.get_upcoming_unplanned_events(db, lookahead_days=28)
    briefs_created = []
    
    for event in upcoming_unplanned:
        brief = await sc.create_seasonal_brief(db, event.id)
        briefs_created.append(brief)
        
    return {
        "status": "success",
        "events_checked": len(upcoming_unplanned),
        "briefs_created": [
            {
                "id": str(b.id),
                "format": b.format,
                "target_platforms": b.target_platforms
            }
            for b in briefs_created
        ]
    }
