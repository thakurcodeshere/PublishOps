"""Video generator — Runway ML Gen-4 + Pexels stock + Ken Burns fallback."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)


class VideoGenerator:
    """Generate video clips using Runway ML, Pexels stock, or Ken Burns fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self._runway_key = settings.RUNWAY_API_KEY
        self._pexels_key = settings.PEXELS_API_KEY
        self._s3 = S3Client()

    async def _generate_runway_clip(
        self, prompt: str, duration: int = 5
    ) -> bytes | None:
        """Generate a video clip using Runway ML Gen-4 Turbo text-to-video."""
        if not self._runway_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Create generation task
                response = await client.post(
                    "https://api.dev.runwayml.com/v1/text_to_video",
                    headers={
                        "Authorization": f"Bearer {self._runway_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text_prompt": prompt,
                        "duration": duration,
                        "model": "gen4_turbo",
                    },
                )
                response.raise_for_status()
                task_data = response.json()
                task_id = task_data.get("id", "")

                if not task_id:
                    logger.error("runway_no_task_id")
                    return None

                # Poll for completion
                for _ in range(120):  # 10 minutes max
                    await asyncio.sleep(5)
                    status_resp = await client.get(
                        f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {self._runway_key}"},
                    )
                    status_resp.raise_for_status()
                    status_data = status_resp.json()
                    status = status_data.get("status", "")

                    if status == "SUCCEEDED":
                        output_url = status_data.get("output", [None])[0]
                        if output_url:
                            video_resp = await client.get(output_url)
                            video_resp.raise_for_status()
                            return video_resp.content
                        return None
                    elif status == "FAILED":
                        logger.error("runway_generation_failed", task_id=task_id)
                        return None

                logger.error("runway_generation_timeout", task_id=task_id)
                return None

        except Exception as exc:
            logger.error("runway_error", error=str(exc))
            return None

    async def _fetch_pexels_broll(
        self, keywords: list[str], count: int = 3
    ) -> list[bytes]:
        """Fetch stock B-roll clips from Pexels."""
        if not self._pexels_key:
            return []

        clips: list[bytes] = []
        query = " ".join(keywords[:3])

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    "https://api.pexels.com/videos/search",
                    params={"query": query, "per_page": count, "orientation": "landscape"},
                    headers={"Authorization": self._pexels_key},
                )
                response.raise_for_status()
                videos = response.json().get("videos", [])

                for video in videos[:count]:
                    # Get the best quality file
                    video_files = video.get("video_files", [])
                    best_file = None
                    for vf in video_files:
                        if vf.get("quality") == "hd":
                            best_file = vf
                            break
                    if not best_file and video_files:
                        best_file = video_files[0]

                    if best_file and best_file.get("link"):
                        vid_resp = await client.get(best_file["link"])
                        vid_resp.raise_for_status()
                        clips.append(vid_resp.content)

        except Exception as exc:
            logger.error("pexels_broll_error", error=str(exc))

        return clips

    async def _create_ken_burns(self, image_data: bytes) -> bytes:
        """Create a Ken Burns effect video from a static image using FFmpeg subprocess."""
        import subprocess
        import tempfile
        import os

        input_path = os.path.join(tempfile.gettempdir(), f"kb_input_{uuid.uuid4().hex}.jpg")
        output_path = os.path.join(tempfile.gettempdir(), f"kb_output_{uuid.uuid4().hex}.mp4")

        try:
            with open(input_path, "wb") as f:
                f.write(image_data)

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", input_path,
                "-vf", "zoompan=z='min(zoom+0.0015,1.5)':d=150:s=1920x1080:fps=30",
                "-c:v", "libx264",
                "-t", "5",
                "-pix_fmt", "yuv420p",
                output_path,
            ]

            proc = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, timeout=60
            )

            if proc.returncode != 0:
                logger.error("ken_burns_ffmpeg_error", stderr=proc.stderr.decode()[:500])
                return b""

            with open(output_path, "rb") as f:
                return f.read()

        finally:
            for path in (input_path, output_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    async def generate_clips(
        self, topic_keywords: list[str], clip_count: int = 3
    ) -> list[str]:
        """
        Generate video clips and upload to S3.

        Strategy:
        1. Try Runway ML Gen-4 Turbo (text-to-video)
        2. Fall back to Pexels stock B-roll
        3. Last resort: Ken Burns on stock image
        """
        s3_keys: list[str] = []
        clip_prefix = f"clips/{uuid.uuid4().hex}"

        # 1. Try Runway
        for i, keyword in enumerate(topic_keywords[:clip_count]):
            prompt = f"Cinematic shot related to {keyword}, professional quality, 4K"
            clip_data = await self._generate_runway_clip(prompt)
            if clip_data:
                key = f"{clip_prefix}/runway_{i}.mp4"
                await self._s3.upload_file(clip_data, key, "video/mp4")
                s3_keys.append(key)

        remaining = clip_count - len(s3_keys)

        # 2. Pexels fallback
        if remaining > 0:
            pexels_clips = await self._fetch_pexels_broll(topic_keywords, remaining)
            for i, clip_data in enumerate(pexels_clips):
                key = f"{clip_prefix}/pexels_{i}.mp4"
                await self._s3.upload_file(clip_data, key, "video/mp4")
                s3_keys.append(key)

        remaining = clip_count - len(s3_keys)

        # 3. Ken Burns fallback (use stock photo)
        if remaining > 0 and self._pexels_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    query = " ".join(topic_keywords[:2])
                    resp = await client.get(
                        "https://api.pexels.com/v1/search",
                        params={"query": query, "per_page": remaining},
                        headers={"Authorization": self._pexels_key},
                    )
                    resp.raise_for_status()
                    photos = resp.json().get("photos", [])

                    for i, photo in enumerate(photos[:remaining]):
                        img_url = photo.get("src", {}).get("large2x", "")
                        if img_url:
                            img_resp = await client.get(img_url)
                            img_resp.raise_for_status()
                            kb_video = await self._create_ken_burns(img_resp.content)
                            if kb_video:
                                key = f"{clip_prefix}/kenburns_{i}.mp4"
                                await self._s3.upload_file(kb_video, key, "video/mp4")
                                s3_keys.append(key)
            except Exception as exc:
                logger.error("ken_burns_fallback_error", error=str(exc))

        logger.info(
            "video_clips_generated",
            total_clips=len(s3_keys),
            requested=clip_count,
            keywords=topic_keywords,
        )
        return s3_keys
