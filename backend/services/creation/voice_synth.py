"""Voice synthesizer using ElevenLabs API with chunked processing."""

from __future__ import annotations

import io
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client
from backend.services.fingerprint.disfluency_calibrator import DisfluencyCalibrator
from backend.models.creator_profile import CreatorProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

logger = get_logger(__name__)

MAX_CHUNK_SIZE = 5000  # Characters per API call


class VoiceSynthesizer:
    """Synthesize speech from text using ElevenLabs API with humanization settings."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.ELEVENLABS_API_KEY
        self._voice_id = settings.ELEVENLABS_VOICE_ID
        self._base_url = "https://api.elevenlabs.io/v1"
        self._s3 = S3Client()
        self.disfluency_calibrator = DisfluencyCalibrator()

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks at sentence boundaries for long scripts."""
        if len(text) <= MAX_CHUNK_SIZE:
            return [text]

        chunks: list[str] = []
        current_chunk = ""

        sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def _synthesize_chunk(
        self,
        text: str,
        voice_id: str | None = None,
        model_id: str = "eleven_turbo_v2_5",
        voice_settings: dict[str, Any] | None = None,
    ) -> bytes:
        """Synthesize a single chunk of text to audio bytes."""
        vid = voice_id or self._voice_id
        
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        }
        if voice_settings:
            default_settings.update(voice_settings)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/text-to-speech/{vid}",
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": default_settings,
                },
            )
            response.raise_for_status()
            return response.content

    async def synthesize(
        self,
        script_text: str,
        voice_id: str | None = None,
        s3_key: str | None = None,
        db: AsyncSession | None = None,
        creator_id: uuid.UUID | None = None,
    ) -> bytes:
        """
        Synthesize full script text to audio.

        Applies creator calibration (disfluency injection, pause insertion) if profile is provided.
        Chunks long scripts (>5000 chars) and concatenates results.
        Optionally uploads to S3.
        """
        voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        }

        processed_text = script_text

        # 1. Run profile calibration adjustments
        if db and creator_id:
            creator_res = await db.execute(
                select(CreatorProfile).where(CreatorProfile.id == creator_id)
            )
            creator = creator_res.scalar_one_or_none()
            if creator:
                # Inject stumbles/fillers
                if creator.disfluency:
                    try:
                        processed_text = self.disfluency_calibrator.inject_disfluencies(
                            script_text, creator.disfluency.profile_data
                        )
                        logger.info("voice_synthesis_disfluency_injected")
                    except Exception as e:
                        logger.warning(f"Failed to inject disfluencies: {e}")

                # Adjust synthesis parameters based on pitch jitter and WPM curves
                if creator.acoustic:
                    ac = creator.acoustic.profile_data
                    jitter = ac.get("pitch_jitter_target_pct", 1.5)
                    # High jitter target means we want a lower stability to allow natural pitch variation
                    if jitter > 2.0:
                        voice_settings["stability"] = 0.40
                    elif jitter < 1.0:
                        voice_settings["stability"] = 0.60
                
                # Add micro pauses at commas to simulate breaths
                processed_text = processed_text.replace(", ", ", ... ")

        chunks = self._chunk_text(processed_text)
        logger.info("voice_synthesis_start", chunks=len(chunks), total_chars=len(processed_text))

        all_audio = bytearray()

        for i, chunk in enumerate(chunks):
            try:
                audio_bytes = await self._synthesize_chunk(chunk, voice_id, voice_settings=voice_settings)
                all_audio.extend(audio_bytes)
                logger.info(
                    "voice_chunk_complete",
                    chunk_index=i + 1,
                    total_chunks=len(chunks),
                    chunk_size=len(chunk),
                    audio_bytes=len(audio_bytes),
                )
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "voice_chunk_error",
                    chunk_index=i + 1,
                    status_code=exc.response.status_code,
                    error=str(exc),
                )
                raise

        result = bytes(all_audio)

        if s3_key:
            await self._s3.upload_file(
                data=result,
                s3_key=s3_key,
                content_type="audio/mpeg",
            )
            logger.info("voice_uploaded_to_s3", s3_key=s3_key, size=len(result))

        logger.info("voice_synthesis_complete", total_size=len(result))
        return result
