"""TikTok optimizer — 9:16, ≤3min, text overlay hook, trending sound, hashtags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TikTokVariant:
    """TikTok-optimised content variant."""

    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    text_overlay_hook: str = ""
    trending_sound_suggestion: str = ""
    aspect_ratio: str = "9:16"
    max_duration_seconds: int = 180
    video_s3_key: str = ""
    specs: dict[str, Any] = field(default_factory=dict)


class TikTokOptimizer:
    """Optimise content for TikTok: short-form vertical video."""

    def optimize(
        self,
        title: str,
        hook_text: str,
        script_text: str = "",
        keywords: list[str] | None = None,
        video_s3_key: str = "",
    ) -> TikTokVariant:
        """Create a TikTok-optimised variant."""
        caption = self._generate_caption(title, keywords or [])
        hashtags = self._generate_hashtags(title, keywords or [])
        text_overlay = self._generate_text_overlay(hook_text, title)
        sound = self._suggest_trending_sound(title)

        variant = TikTokVariant(
            caption=caption,
            hashtags=hashtags,
            text_overlay_hook=text_overlay,
            trending_sound_suggestion=sound,
            video_s3_key=video_s3_key,
            specs={
                "aspect_ratio": "9:16",
                "resolution": "1080x1920",
                "max_duration": "3 minutes",
                "format": "mp4",
                "codec": "h264",
                "text_position": "center_top",
                "text_font": "bold_sans",
            },
        )

        logger.info("tiktok_optimized", title=title[:60], hashtags=len(hashtags))
        return variant

    def _generate_caption(self, title: str, keywords: list[str]) -> str:
        """Generate TikTok caption (short, punchy)."""
        caption = title
        if len(caption) > 100:
            caption = caption[:97] + "..."
        return caption

    def _generate_hashtags(self, title: str, keywords: list[str]) -> list[str]:
        """Generate 3-5 relevant hashtags."""
        hashtags = ["fyp", "foryou"]

        for word in title.split()[:3]:
            clean = word.strip(",.!?;:").lower()
            if len(clean) > 2:
                hashtags.append(clean)

        for kw in keywords[:2]:
            tag = kw.replace(" ", "").lower()
            if tag not in hashtags:
                hashtags.append(tag)

        return [f"#{h}" for h in hashtags[:5]]

    def _generate_text_overlay(self, hook_text: str, title: str) -> str:
        """Generate text overlay for the first frame hook."""
        overlay = hook_text if hook_text else title
        if len(overlay) > 50:
            overlay = overlay[:47] + "..."
        return overlay.upper()

    def _suggest_trending_sound(self, title: str) -> str:
        """Suggest a trending sound category based on content type."""
        title_lower = title.lower()
        if any(w in title_lower for w in ["funny", "meme", "comedy"]):
            return "Trending comedy sound — check TikTok Creative Center"
        elif any(w in title_lower for w in ["learn", "how", "tutorial"]):
            return "Educational beat — check TikTok Creative Center"
        elif any(w in title_lower for w in ["news", "breaking", "update"]):
            return "Dramatic news sound — check TikTok Creative Center"
        return "Original sound or trending beat — check TikTok Creative Center"
