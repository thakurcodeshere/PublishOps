"""YouTube optimizer — 16:9, SEO title, description, tags, chapters, SRT."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class YouTubeVariant:
    """YouTube-optimised content variant."""

    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    chapters: list[dict[str, str]] = field(default_factory=list)
    srt_subtitles: str = ""
    aspect_ratio: str = "16:9"
    resolution: str = "1080p"
    thumbnail_s3_key: str = ""
    video_s3_key: str = ""
    specs: dict[str, Any] = field(default_factory=dict)


class YouTubeOptimizer:
    """Optimise content for YouTube: SEO, metadata, chapters, and subtitles."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def optimize(
        self,
        title: str,
        script_text: str,
        keywords: list[str] | None = None,
        video_s3_key: str = "",
        thumbnail_s3_key: str = "",
    ) -> YouTubeVariant:
        """Create a YouTube-optimised variant."""
        seo_title = await self._generate_seo_title(title, keywords or [])
        description = await self._generate_description(title, script_text, keywords or [])
        tags = self._generate_tags(title, keywords or [])
        chapters = self._generate_chapters(script_text)
        srt = self._generate_srt(script_text)

        variant = YouTubeVariant(
            title=seo_title,
            description=description,
            tags=tags,
            chapters=chapters,
            srt_subtitles=srt,
            video_s3_key=video_s3_key,
            thumbnail_s3_key=thumbnail_s3_key,
            specs={
                "max_title_length": 60,
                "max_description_length": 5000,
                "max_tags": 30,
                "resolution": "1080p+",
                "aspect_ratio": "16:9",
                "format": "mp4",
                "codec": "h264",
            },
        )

        logger.info(
            "youtube_optimized",
            title=seo_title[:60],
            tags=len(tags),
            chapters=len(chapters),
        )
        return variant

    async def _generate_seo_title(self, title: str, keywords: list[str]) -> str:
        """Generate SEO-optimised title (≤60 chars)."""
        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": f"Write a YouTube SEO title (max 60 characters) for this topic. Include a power word and create curiosity.\n\nTopic: {title}\nKeywords: {', '.join(keywords)}\n\nReturn ONLY the title text.",
                    }
                ],
            )
            seo_title = response.content[0].text.strip().strip('"\'')
            return seo_title[:60]
        except Exception:
            return title[:60]

    async def _generate_description(
        self, title: str, script_text: str, keywords: list[str]
    ) -> str:
        """Generate YouTube description (≤5000 chars) with SEO keywords."""
        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Write a YouTube video description (max 5000 chars) for:
Title: {title}
Keywords: {', '.join(keywords)}
Script excerpt: {script_text[:500]}

Include: hook paragraph, key points summary, relevant links placeholders, social media links placeholders, 3-5 related keywords naturally.
Return ONLY the description.""",
                    }
                ],
            )
            return response.content[0].text.strip()[:5000]
        except Exception:
            return f"{title}\n\nIn this video, we explore {title}.\n\nKeywords: {', '.join(keywords)}"

    def _generate_tags(self, title: str, keywords: list[str]) -> list[str]:
        """Generate YouTube tags (max 30)."""
        tags: list[str] = []
        # Add title words
        for word in title.split():
            clean = word.strip(",.!?;:").lower()
            if len(clean) > 2 and clean not in tags:
                tags.append(clean)
        # Add keywords
        for kw in keywords:
            if kw.lower() not in tags:
                tags.append(kw.lower())
        # Add common suffixes
        for suffix in ["tutorial", "explained", "guide", "2026", "tips"]:
            combined = f"{title.split()[0].lower()} {suffix}" if title else suffix
            if combined not in tags:
                tags.append(combined)

        return tags[:30]

    def _generate_chapters(self, script_text: str) -> list[dict[str, str]]:
        """Generate chapter markers from script timestamps."""
        chapters: list[dict[str, str]] = []
        sections = script_text.split("[")

        timestamp = "0:00"
        for section in sections:
            if "]" in section:
                marker, content = section.split("]", 1)
                marker = marker.strip()
                if marker in ("HOOK", "BODY", "CTA"):
                    chapter_titles = {
                        "HOOK": "Introduction",
                        "BODY": "Main Content",
                        "CTA": "Wrap Up & Next Steps",
                    }
                    chapters.append({
                        "timestamp": timestamp,
                        "title": chapter_titles.get(marker, marker),
                    })
                    # Estimate next timestamp
                    word_count = len(content.split())
                    minutes = word_count // 150  # ~150 wpm
                    seconds = (word_count % 150) * 60 // 150
                    total_seconds = int(timestamp.split(":")[0]) * 60 + int(timestamp.split(":")[1]) + minutes * 60 + seconds
                    timestamp = f"{total_seconds // 60}:{total_seconds % 60:02d}"

        if not chapters:
            chapters = [{"timestamp": "0:00", "title": "Introduction"}]

        return chapters

    def _generate_srt(self, script_text: str) -> str:
        """Generate basic SRT subtitles from script text."""
        lines = [l.strip() for l in script_text.split(".") if l.strip()]
        srt_parts: list[str] = []
        seconds = 0

        for i, line in enumerate(lines[:100]):  # Cap at 100 lines
            start_h = seconds // 3600
            start_m = (seconds % 3600) // 60
            start_s = seconds % 60
            duration = max(2, len(line.split()) // 3)
            end = seconds + duration
            end_h = end // 3600
            end_m = (end % 3600) // 60
            end_s = end % 60

            srt_parts.append(
                f"{i + 1}\n"
                f"{start_h:02d}:{start_m:02d}:{start_s:02d},000 --> "
                f"{end_h:02d}:{end_m:02d}:{end_s:02d},000\n"
                f"{line.strip()}\n"
            )
            seconds = end

        return "\n".join(srt_parts)
