"""Video assembler — FFmpeg-based merging of audio, video, and subtitles."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import uuid
from typing import Any

from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}


class VideoAssembler:
    """Assemble final video from audio, video clips, and subtitles using FFmpeg."""

    def __init__(self) -> None:
        self._s3 = S3Client()

    async def _download_to_temp(self, s3_key: str, suffix: str) -> str:
        """Download S3 file to a temp path."""
        data = await self._s3.download_file(s3_key)
        path = os.path.join(tempfile.gettempdir(), f"asm_{uuid.uuid4().hex}{suffix}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _create_subtitle_file(self, subtitle_text: str, output_path: str) -> None:
        """Create an ASS subtitle file from plain text."""
        lines = subtitle_text.split("\n")
        duration_per_line = 4.0  # seconds

        ass_content = """[Script Info]
Title: PublishOps Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            start_time = i * duration_per_line
            end_time = start_time + duration_per_line
            start_str = self._seconds_to_ass_time(start_time)
            end_str = self._seconds_to_ass_time(end_time)
            ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line.strip()}\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    @staticmethod
    def _seconds_to_ass_time(seconds: float) -> str:
        """Convert seconds to ASS time format H:MM:SS.CC"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    async def _run_ffmpeg(self, cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
        """Run FFmpeg command in a thread."""
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, timeout=600
        )
        if result.returncode != 0:
            stderr = result.stderr.decode()[:1000]
            logger.error("ffmpeg_error", cmd=" ".join(cmd[:5]), stderr=stderr)
            raise RuntimeError(f"FFmpeg failed: {stderr}")
        return result

    async def _concat_videos(self, video_paths: list[str], output_path: str) -> None:
        """Concatenate multiple video clips with crossfade transitions."""
        if len(video_paths) == 1:
            # Single clip, just copy
            import shutil
            shutil.copy2(video_paths[0], output_path)
            return

        # Create concat file
        concat_file = os.path.join(tempfile.gettempdir(), f"concat_{uuid.uuid4().hex}.txt")
        with open(concat_file, "w") as f:
            for vp in video_paths:
                f.write(f"file '{vp}'\n")

        # Build filter for crossfade (0.5s transitions)
        if len(video_paths) == 2:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_paths[0],
                "-i", video_paths[1],
                "-filter_complex",
                "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4[outv]",
                "-map", "[outv]",
                "-c:v", "libx264", "-preset", "fast",
                "-pix_fmt", "yuv420p",
                output_path,
            ]
        else:
            # For 3+ clips, use concat demuxer (simpler, no xfade)
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264", "-preset", "fast",
                "-pix_fmt", "yuv420p",
                output_path,
            ]

        await self._run_ffmpeg(cmd)

        try:
            os.unlink(concat_file)
        except OSError:
            pass

    async def assemble(
        self,
        audio_s3_key: str,
        video_clip_s3_keys: list[str],
        subtitle_text: str = "",
        aspect_ratios: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Assemble final video from audio, video clips, and subtitles.

        Returns dict of {aspect_ratio: s3_key} for each output.
        """
        ratios = aspect_ratios or ["16:9", "9:16", "1:1", "4:5"]
        temp_files: list[str] = []
        results: dict[str, str] = {}

        try:
            # Download all assets
            audio_path = await self._download_to_temp(audio_s3_key, ".mp3")
            temp_files.append(audio_path)

            video_paths: list[str] = []
            for key in video_clip_s3_keys:
                path = await self._download_to_temp(key, ".mp4")
                video_paths.append(path)
                temp_files.append(path)

            if not video_paths:
                logger.error("no_video_clips_for_assembly")
                return results

            # Concatenate clips
            concat_path = os.path.join(tempfile.gettempdir(), f"concat_{uuid.uuid4().hex}.mp4")
            temp_files.append(concat_path)
            await self._concat_videos(video_paths, concat_path)

            # Create subtitle file if provided
            sub_path = ""
            if subtitle_text:
                sub_path = os.path.join(tempfile.gettempdir(), f"subs_{uuid.uuid4().hex}.ass")
                self._create_subtitle_file(subtitle_text, sub_path)
                temp_files.append(sub_path)

            # Generate each aspect ratio
            for ratio in ratios:
                width, height = ASPECT_RATIOS.get(ratio, (1920, 1080))
                output_path = os.path.join(
                    tempfile.gettempdir(), f"final_{uuid.uuid4().hex}_{ratio.replace(':', 'x')}.mp4"
                )
                temp_files.append(output_path)

                # Build FFmpeg command
                vf_filters = [
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                ]
                if sub_path:
                    vf_filters.append(f"ass={sub_path}")

                cmd = [
                    "ffmpeg", "-y",
                    "-i", concat_path,
                    "-i", audio_path,
                    "-vf", ",".join(vf_filters),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-shortest",
                    "-pix_fmt", "yuv420p",
                    output_path,
                ]

                await self._run_ffmpeg(cmd)

                # Upload to S3
                with open(output_path, "rb") as f:
                    output_data = f.read()

                s3_key = f"videos/{uuid.uuid4().hex}/{ratio.replace(':', 'x')}.mp4"
                await self._s3.upload_file(output_data, s3_key, "video/mp4")
                results[ratio] = s3_key

                logger.info(
                    "video_assembled",
                    aspect_ratio=ratio,
                    s3_key=s3_key,
                    size=len(output_data),
                )

        finally:
            for path in temp_files:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        logger.info("assembly_complete", outputs=len(results))
        return results
