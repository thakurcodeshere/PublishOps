"""Creation pipeline orchestrator — chains script → voice → enhance → video → assembly → thumbnail."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import AssetStage, AssetStatus, AssetType, ContentAsset, ContentBrief
from backend.services.creation.audio_enhance import AudioEnhancer
from backend.services.creation.script_writer import ScriptWriter
from backend.services.creation.thumbnail_gen import ThumbnailGenerator
from backend.services.creation.video_assembly import VideoAssembler
from backend.services.creation.video_gen import VideoGenerator
from backend.services.creation.voice_synth import VoiceSynthesizer
from backend.services.strategy.brief_generator import ContentBrief as BriefData
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)


class CreationPipeline:
    """Orchestrate the full content creation pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._script_writer = ScriptWriter()
        self._voice_synth = VoiceSynthesizer()
        self._audio_enhancer = AudioEnhancer()
        self._video_gen = VideoGenerator()
        self._assembler = VideoAssembler()
        self._thumbnail_gen = ThumbnailGenerator()
        self._s3 = S3Client()

    async def _record_asset(
        self,
        brief_id: uuid.UUID,
        asset_type: AssetType,
        s3_key: str,
        stage: AssetStage,
        status: AssetStatus,
        metadata: dict[str, Any] | None = None,
        duration_secs: float | None = None,
        file_size: int | None = None,
        error_log: str | None = None,
    ) -> ContentAsset:
        """Create a content asset record in the database."""
        from backend.config import get_settings
        settings = get_settings()
        s3_url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}" if s3_key else None

        asset = ContentAsset(
            brief_id=brief_id,
            asset_type=asset_type,
            s3_key=s3_key or None,
            s3_url=s3_url,
            file_size_bytes=file_size,
            duration_secs=duration_secs,
            metadata=metadata or {},
            stage=stage,
            status=status,
            error_log=error_log,
        )
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def run(
        self,
        brief: ContentBrief,
        brief_data: BriefData,
        platform: str = "youtube",
        creator_id: uuid.UUID | None = None,
    ) -> list[ContentAsset]:
        """
        Execute the full creation pipeline for a content brief.

        Steps: script → viral_gate → voice → audio_enhance → video → assembly → thumbnail
        On failure, marks the asset status and stops.
        """
        brief_id = brief.id
        assets: list[ContentAsset] = []
        prefix = f"content/{brief_id}"

        logger.info("creation_pipeline_start", brief_id=str(brief_id), platform=platform, creator_id=str(creator_id))

        # 1. Generate script
        try:
            script = await self._script_writer.generate_script(brief_data, platform, db=self._session, creator_id=creator_id)
            
            # 1b. Run through Viral Score Gate (with up to 2 retries)
            from backend.services.creation.viral_gate import ViralScoreGate
            gate = ViralScoreGate()
            score_result = await gate.predict_virality(self._session, brief_id, script.full_text_a)
            
            retries = 0
            while not score_result.passed_gate and retries < 2:
                logger.info(
                    "creation_pipeline_viral_gate_failed_retrying",
                    brief_id=str(brief_id),
                    score=score_result.composite_score,
                    retry=retries + 1
                )
                # Adjust prompt angle instructions slightly
                brief_data.tone_notes = (brief_data.tone_notes or "") + " Make the hook extremely punchy, use shorter sentences, increase tension, and call to action clearly."
                script = await self._script_writer.generate_script(brief_data, platform, db=self._session, creator_id=creator_id)
                score_result = await gate.predict_virality(self._session, brief_id, script.full_text_a)
                retries += 1
                
            if not score_result.passed_gate:
                await self._record_asset(
                    brief_id=brief_id,
                    asset_type=AssetType.SCRIPT,
                    s3_key="",
                    stage=AssetStage.SCRIPT,
                    status=AssetStatus.FAILED,
                    error_log=f"Script failed the viral score gate. Final score: {score_result.composite_score}",
                )
                logger.error("pipeline_viral_gate_failed_termination", brief_id=str(brief_id), score=score_result.composite_score)
                return assets

            import json
            script_bytes = json.dumps({
                "variant_a": script.variant_a,
                "variant_b": script.variant_b,
                "platform": script.platform,
                "viral_score": score_result.composite_score,
            }).encode()
            await self._s3.upload_file(script_bytes, script_s3_key := f"{prefix}/script.json", "application/json")

            script_asset = await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.SCRIPT,
                s3_key=script_s3_key,
                stage=AssetStage.SCRIPT,
                status=AssetStatus.COMPLETED,
                metadata={"word_count_a": script.variant_a.get("word_count", 0), "viral_score": score_result.composite_score},
                file_size=len(script_bytes),
            )
            assets.append(script_asset)
            logger.info("pipeline_stage_complete", stage="script", brief_id=str(brief_id))

        except Exception as exc:
            await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.SCRIPT,
                s3_key="",
                stage=AssetStage.SCRIPT,
                status=AssetStatus.FAILED,
                error_log=str(exc),
            )
            logger.error("pipeline_script_failed", error=str(exc))
            return assets

        # 2. Voice synthesis
        try:
            audio_s3_key = f"{prefix}/audio_raw.mp3"
            audio_bytes = await self._voice_synth.synthesize(
                script.full_text_a, s3_key=audio_s3_key, db=self._session, creator_id=creator_id
            )

            audio_asset = await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.AUDIO_RAW,
                s3_key=audio_s3_key,
                stage=AssetStage.VOICE,
                status=AssetStatus.COMPLETED,
                file_size=len(audio_bytes),
            )
            assets.append(audio_asset)
            logger.info("pipeline_stage_complete", stage="voice", brief_id=str(brief_id))

        except Exception as exc:
            await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.AUDIO_RAW,
                s3_key="",
                stage=AssetStage.VOICE,
                status=AssetStatus.FAILED,
                error_log=str(exc),
            )
            logger.error("pipeline_voice_failed", error=str(exc))
            return assets

        # 3. Audio enhancement
        try:
            enhanced_s3_key = await self._audio_enhancer.enhance(audio_s3_key)

            enhanced_asset = await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.AUDIO_ENHANCED,
                s3_key=enhanced_s3_key,
                stage=AssetStage.AUDIO_ENHANCE,
                status=AssetStatus.COMPLETED,
            )
            assets.append(enhanced_asset)
            final_audio_key = enhanced_s3_key
            logger.info("pipeline_stage_complete", stage="audio_enhance", brief_id=str(brief_id))

        except Exception as exc:
            logger.warning("pipeline_audio_enhance_failed_using_raw", error=str(exc))
            final_audio_key = audio_s3_key  # Fall back to raw audio

        # 4. Video generation
        try:
            keywords = brief_data.topic_title.split()[:5]
            clip_keys = await self._video_gen.generate_clips(keywords, clip_count=3)

            for i, key in enumerate(clip_keys):
                clip_asset = await self._record_asset(
                    brief_id=brief_id,
                    asset_type=AssetType.VIDEO_CLIP,
                    s3_key=key,
                    stage=AssetStage.VIDEO_GEN,
                    status=AssetStatus.COMPLETED,
                    metadata={"clip_index": i},
                )
                assets.append(clip_asset)

            logger.info("pipeline_stage_complete", stage="video_gen", clips=len(clip_keys))

        except Exception as exc:
            await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.VIDEO_CLIP,
                s3_key="",
                stage=AssetStage.VIDEO_GEN,
                status=AssetStatus.FAILED,
                error_log=str(exc),
            )
            logger.error("pipeline_video_gen_failed", error=str(exc))
            return assets

        # 5. Video assembly
        try:
            subtitle_text = script.full_text_a
            assembled = await self._assembler.assemble(
                audio_s3_key=final_audio_key,
                video_clip_s3_keys=clip_keys,
                subtitle_text=subtitle_text,
            )

            for ratio, key in assembled.items():
                video_asset = await self._record_asset(
                    brief_id=brief_id,
                    asset_type=AssetType.VIDEO_ASSEMBLED,
                    s3_key=key,
                    stage=AssetStage.ASSEMBLY,
                    status=AssetStatus.COMPLETED,
                    metadata={"aspect_ratio": ratio},
                )
                assets.append(video_asset)

            logger.info("pipeline_stage_complete", stage="assembly", ratios=len(assembled))

        except Exception as exc:
            await self._record_asset(
                brief_id=brief_id,
                asset_type=AssetType.VIDEO_ASSEMBLED,
                s3_key="",
                stage=AssetStage.ASSEMBLY,
                status=AssetStatus.FAILED,
                error_log=str(exc),
            )
            logger.error("pipeline_assembly_failed", error=str(exc))
            return assets

        # 6. Thumbnail generation
        try:
            thumb_keys = await self._thumbnail_gen.generate_quad(
                title=brief_data.topic_title,
                hook_text=brief_data.hook_text,
            )

            for key in thumb_keys:
                if key:
                    thumb_asset = await self._record_asset(
                        brief_id=brief_id,
                        asset_type=AssetType.THUMBNAIL,
                        s3_key=key,
                        stage=AssetStage.THUMBNAIL,
                        status=AssetStatus.COMPLETED,
                    )
                    assets.append(thumb_asset)

            logger.info("pipeline_stage_complete", stage="thumbnail")

        except Exception as exc:
            logger.warning("pipeline_thumbnail_failed", error=str(exc))
            # Thumbnails are optional; pipeline continues

        logger.info(
            "creation_pipeline_complete",
            brief_id=str(brief_id),
            total_assets=len(assets),
        )
        return assets
