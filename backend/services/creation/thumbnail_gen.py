"""Thumbnail generator using Bannerbear API for A/B variant generation."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)


class ThumbnailGenerator:
    """Generate thumbnail pairs using the Bannerbear API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.BANNERBEAR_API_KEY
        self._base_url = "https://api.bannerbear.com/v2"
        self._s3 = S3Client()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _create_image(
        self,
        template_uid: str,
        modifications: list[dict[str, Any]],
    ) -> str | None:
        """Create an image via Bannerbear API and return the image URL."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/images",
                headers=self._auth_headers(),
                json={
                    "template": template_uid,
                    "modifications": modifications,
                },
            )
            response.raise_for_status()
            image_data = response.json()
            image_uid = image_data.get("uid", "")

            # Poll for completion
            for _ in range(30):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    f"{self._base_url}/images/{image_uid}",
                    headers=self._auth_headers(),
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()

                if status_data.get("status") == "completed":
                    return status_data.get("image_url")
                elif status_data.get("status") == "failed":
                    logger.error("bannerbear_image_failed", uid=image_uid)
                    return None

            logger.error("bannerbear_image_timeout", uid=image_uid)
            return None

    async def _download_image(self, url: str) -> bytes:
        """Download an image from URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def generate_pair(
        self,
        title: str,
        hook_text: str,
        face_image_url: str = "",
        template_a_uid: str = "default_template_a",
        template_b_uid: str = "default_template_b",
    ) -> tuple[str, str]:
        """
        Generate an A/B pair of thumbnails.

        Returns (thumb_a_s3_key, thumb_b_s3_key).
        """
        logger.info("thumbnail_generation_start", title=title[:60])

        # Variant A: bold text, warm colors
        mods_a: list[dict[str, Any]] = [
            {"name": "title", "text": title[:40]},
            {"name": "hook", "text": hook_text[:60]},
        ]
        if face_image_url:
            mods_a.append({"name": "face", "image_url": face_image_url})

        # Variant B: different text treatment, cool colors
        mods_b: list[dict[str, Any]] = [
            {"name": "title", "text": title[:40].upper()},
            {"name": "hook", "text": hook_text[:60]},
        ]
        if face_image_url:
            mods_b.append({"name": "face", "image_url": face_image_url})

        # Generate both variants concurrently
        url_a, url_b = await asyncio.gather(
            self._create_image(template_a_uid, mods_a),
            self._create_image(template_b_uid, mods_b),
        )

        prefix = f"thumbnails/{uuid.uuid4().hex}"
        s3_key_a = f"{prefix}/variant_a.png"
        s3_key_b = f"{prefix}/variant_b.png"

        if url_a:
            img_data = await self._download_image(url_a)
            await self._s3.upload_file(img_data, s3_key_a, "image/png")
        else:
            logger.warning("thumbnail_a_generation_failed")
            s3_key_a = ""

        if url_b:
            img_data = await self._download_image(url_b)
            await self._s3.upload_file(img_data, s3_key_b, "image/png")
        else:
            logger.warning("thumbnail_b_generation_failed")
            s3_key_b = ""

        logger.info(
            "thumbnails_generated",
            s3_key_a=s3_key_a,
            s3_key_b=s3_key_b,
        )
        return (s3_key_a, s3_key_b)

    async def generate_quad(
        self,
        title: str,
        hook_text: str,
        face_image_url: str = "",
        template_uid: str = "default_template",
    ) -> list[str]:
        """
        Generate 4 distinct thumbnail variants (A, B, C, D).

        Returns list of S3 keys.
        """
        logger.info("thumbnail_quad_generation_start", title=title[:60])

        # Variant A: Standard
        mods_a = [
            {"name": "title", "text": title[:40]},
            {"name": "hook", "text": hook_text[:60]},
        ]
        # Variant B: Uppercase Attention
        mods_b = [
            {"name": "title", "text": title[:40].upper()},
            {"name": "hook", "text": f"MUST WATCH: {hook_text[:45]}"},
        ]
        # Variant C: Question / Curiosities
        mods_c = [
            {"name": "title", "text": f"Wait, {title[:35]}?"},
            {"name": "hook", "text": "Is this actually true?"},
        ]
        # Variant D: Action oriented
        mods_d = [
            {"name": "title", "text": "DO THIS INSTEAD!"},
            {"name": "hook", "text": title[:50]},
        ]

        for mods in [mods_a, mods_b, mods_c, mods_d]:
            if face_image_url:
                mods.append({"name": "face", "image_url": face_image_url})

        # Generate 4 variants concurrently
        urls = await asyncio.gather(
            self._create_image(template_uid, mods_a),
            self._create_image(template_uid, mods_b),
            self._create_image(template_uid, mods_c),
            self._create_image(template_uid, mods_d),
            return_exceptions=True
        )

        prefix = f"thumbnails/{uuid.uuid4().hex}"
        keys = []
        
        for idx, url in enumerate(urls):
            if url and not isinstance(url, Exception):
                s3_key = f"{prefix}/variant_{chr(97 + idx)}.png" # variant_a, variant_b, etc.
                try:
                    img_data = await self._download_image(url)
                    await self._s3.upload_file(img_data, s3_key, "image/png")
                    keys.append(s3_key)
                except Exception as e:
                    logger.warning(f"Failed to process thumbnail variant {idx}: {e}")
                    keys.append("")
            else:
                logger.warning(f"Thumbnail variant {idx} generation failed or timed out")
                keys.append("")
                
        return keys
