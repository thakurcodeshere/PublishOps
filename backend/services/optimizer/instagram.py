"""Instagram optimizer — Carousel + Reels with save-optimised captions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InstagramVariant:
    """Instagram-optimised content variant (Carousel + Reel)."""

    reel_caption: str = ""
    carousel_caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    carousel_slides: list[dict[str, str]] = field(default_factory=list)
    reel_aspect_ratio: str = "9:16"
    carousel_aspect_ratio: str = "4:5"
    reel_s3_key: str = ""
    carousel_s3_keys: list[str] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)


class InstagramOptimizer:
    """Optimise content for Instagram: Carousel (1:1/4:5) + Reels (9:16)."""

    def optimize(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str = "",
        keywords: list[str] | None = None,
        video_s3_key: str = "",
    ) -> InstagramVariant:
        """Create an Instagram-optimised variant."""
        reel_caption = self._generate_reel_caption(title, hook_text)
        carousel_caption = self._generate_carousel_caption(title)
        hashtags = self._generate_hashtags(title, keywords or [])
        slides = self._generate_carousel_slides(title, talking_points, hook_text)

        variant = InstagramVariant(
            reel_caption=reel_caption,
            carousel_caption=carousel_caption,
            hashtags=hashtags,
            carousel_slides=slides,
            reel_s3_key=video_s3_key,
            specs={
                "reel_aspect_ratio": "9:16",
                "reel_resolution": "1080x1920",
                "reel_max_duration": "90 seconds",
                "carousel_aspect_ratio": "4:5 or 1:1",
                "carousel_resolution": "1080x1350 or 1080x1080",
                "carousel_max_slides": 10,
                "format": "mp4/jpg",
                "carousel_font": "sans-serif bold",
            },
        )

        logger.info(
            "instagram_optimized",
            title=title[:60],
            hashtags=len(hashtags),
            slides=len(slides),
        )
        return variant

    def _generate_reel_caption(self, title: str, hook_text: str) -> str:
        """Generate a save-optimised Reel caption."""
        parts: list[str] = []
        if hook_text:
            parts.append(hook_text)
        parts.append("")
        parts.append(title)
        parts.append("")
        parts.append("💾 Save this for later")
        parts.append("📤 Share with someone who needs to see this")
        parts.append("")
        parts.append("Follow for more content like this ✨")
        return "\n".join(parts)

    def _generate_carousel_caption(self, title: str) -> str:
        """Generate a save-optimised Carousel caption."""
        parts: list[str] = []
        parts.append(f"📌 {title}")
        parts.append("")
        parts.append("Swipe through for all the details →")
        parts.append("")
        parts.append("💾 Save this post to reference later")
        parts.append("👥 Tag someone who should see this")
        parts.append("")
        parts.append("Drop a 🔥 if you found this valuable")
        return "\n".join(parts)

    def _generate_hashtags(self, title: str, keywords: list[str]) -> list[str]:
        """Generate 20-30 Instagram hashtags in tiered sizes."""
        hashtags: list[str] = []

        # Large hashtags (>1M posts)
        large = ["instagood", "viral", "trending", "explore", "fyp"]
        hashtags.extend(large)

        # Medium hashtags (100K-1M posts) based on content
        for word in title.split()[:5]:
            clean = word.strip(",.!?;:").lower()
            if len(clean) > 3:
                hashtags.append(clean)

        # Keyword-based hashtags
        for kw in keywords:
            tag = kw.replace(" ", "").lower()
            if tag not in hashtags:
                hashtags.append(tag)

        # Niche hashtags
        niche = ["contentcreator", "valuecontent", "learnontiktok", "educationalcontent",
                 "digitalcreator", "creatorlife", "growthmindset", "infographic",
                 "carouselpost", "savethispost", "knowledgeispower"]
        for h in niche:
            if h not in hashtags:
                hashtags.append(h)

        return [f"#{h}" for h in hashtags[:30]]

    def _generate_carousel_slides(
        self, title: str, talking_points: list[str], hook_text: str
    ) -> list[dict[str, str]]:
        """Generate carousel slide content (max 10 slides)."""
        slides: list[dict[str, str]] = []

        # Slide 1: Hook/Title
        slides.append({
            "slide_number": "1",
            "type": "title",
            "headline": hook_text or title,
            "subtext": "Swipe to learn more →",
        })

        # Content slides from talking points
        for i, point in enumerate(talking_points[:7]):
            slides.append({
                "slide_number": str(i + 2),
                "type": "content",
                "headline": f"Point {i + 1}",
                "body": point,
            })

        # Summary slide
        if len(slides) < 10:
            slides.append({
                "slide_number": str(len(slides) + 1),
                "type": "summary",
                "headline": "Key Takeaways",
                "body": " • ".join(tp[:50] for tp in talking_points[:3]),
            })

        # CTA slide
        if len(slides) < 10:
            slides.append({
                "slide_number": str(len(slides) + 1),
                "type": "cta",
                "headline": "Found this valuable?",
                "body": "💾 Save • 📤 Share • 👤 Follow for more",
            })

        return slides[:10]
