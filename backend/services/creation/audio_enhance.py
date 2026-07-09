"""Audio enhancer using Auphonic API for professional mastering."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)

POLL_INTERVAL = 10  # seconds
MAX_POLLS = 60  # 10 minutes max


class AudioEnhancer:
    """Enhance audio via Auphonic API for loudness normalisation and noise reduction."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.AUPHONIC_API_KEY
        self._base_url = "https://auphonic.com/api"
        self._s3 = S3Client()

    def _auth(self) -> tuple[str, str]:
        return ("", self._api_key)

    async def enhance(self, s3_audio_key: str) -> str:
        """
        Enhance audio via Auphonic.

        1. Download from S3
        2. Create Auphonic production
        3. Upload audio to the production
        4. Start processing
        5. Poll for completion
        6. Download enhanced audio
        7. Upload back to S3

        Returns the S3 key of the enhanced audio.
        """
        logger.info("audio_enhance_start", s3_key=s3_audio_key)

        # 1. Download audio from S3
        audio_data = await self._s3.download_file(s3_audio_key)

        async with httpx.AsyncClient(timeout=120.0) as client:
            # 2. Create production
            prod_response = await client.post(
                f"{self._base_url}/productions.json",
                auth=self._auth(),
                json={
                    "metadata": {"title": f"PublishOps Enhancement: {s3_audio_key}"},
                    "algorithms": {
                        "loudnesstarget": -16,
                        "leveler": True,
                        "noise_reduction": True,
                        "filtering": True,
                    },
                    "output_files": [{"format": "mp3", "bitrate": 192}],
                },
            )
            prod_response.raise_for_status()
            prod_data = prod_response.json()
            prod_uuid = prod_data["data"]["uuid"]
            logger.info("auphonic_production_created", uuid=prod_uuid)

            # 3. Upload audio to production
            upload_response = await client.post(
                f"{self._base_url}/production/{prod_uuid}/upload.json",
                auth=self._auth(),
                files={"input_file": ("audio.mp3", audio_data, "audio/mpeg")},
            )
            upload_response.raise_for_status()

            # 4. Start processing
            start_response = await client.post(
                f"{self._base_url}/production/{prod_uuid}/start.json",
                auth=self._auth(),
            )
            start_response.raise_for_status()
            logger.info("auphonic_processing_started", uuid=prod_uuid)

            # 5. Poll for completion
            enhanced_url = ""
            for attempt in range(MAX_POLLS):
                await asyncio.sleep(POLL_INTERVAL)
                status_response = await client.get(
                    f"{self._base_url}/production/{prod_uuid}.json",
                    auth=self._auth(),
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                status = status_data["data"]["status"]

                if status == 3:  # Done
                    output_files = status_data["data"].get("output_files", [])
                    if output_files:
                        enhanced_url = output_files[0].get("download_url", "")
                    logger.info("auphonic_processing_complete", uuid=prod_uuid, polls=attempt + 1)
                    break
                elif status == 9:  # Error
                    error_msg = status_data["data"].get("error_message", "Unknown error")
                    logger.error("auphonic_processing_error", uuid=prod_uuid, error=error_msg)
                    raise RuntimeError(f"Auphonic processing failed: {error_msg}")
                else:
                    logger.debug("auphonic_polling", uuid=prod_uuid, status=status, attempt=attempt + 1)
            else:
                raise TimeoutError(f"Auphonic processing timed out after {MAX_POLLS * POLL_INTERVAL}s")

            # 6. Download enhanced audio
            if not enhanced_url:
                raise RuntimeError("No download URL returned from Auphonic")

            download_response = await client.get(enhanced_url, auth=self._auth())
            download_response.raise_for_status()
            enhanced_audio = download_response.content

        # 7. Upload back to S3
        enhanced_s3_key = s3_audio_key.replace(".mp3", "_enhanced.mp3").replace(
            ".wav", "_enhanced.wav"
        )
        if enhanced_s3_key == s3_audio_key:
            enhanced_s3_key = f"{s3_audio_key}_enhanced"

        await self._s3.upload_file(
            data=enhanced_audio,
            s3_key=enhanced_s3_key,
            content_type="audio/mpeg",
        )

        logger.info(
            "audio_enhance_complete",
            original_key=s3_audio_key,
            enhanced_key=enhanced_s3_key,
            original_size=len(audio_data),
            enhanced_size=len(enhanced_audio),
        )
        return enhanced_s3_key
