"""LinkedIn optimizer — text-first, PDF carousel, professional tone."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LinkedInVariant:
    """LinkedIn-optimised content variant."""

    text_post: str = ""
    hashtags: list[str] = field(default_factory=list)
    pdf_carousel_slides: list[dict[str, str]] = field(default_factory=list)
    pdf_s3_key: str = ""
    media_s3_keys: list[str] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)


class LinkedInOptimizer:
    """Optimise content for LinkedIn: text-first with PDF carousel option."""

    MAX_POST_LENGTH = 3000

    def optimize(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str = "",
        cta_text: str = "",
        keywords: list[str] | None = None,
        media_s3_keys: list[str] | None = None,
    ) -> LinkedInVariant:
        """Create a LinkedIn-optimised variant."""
        text_post = self._generate_text_post(title, talking_points, hook_text, cta_text)
        hashtags = self._generate_hashtags(keywords or [])
        carousel_slides = self._generate_pdf_carousel(title, talking_points, hook_text)

        variant = LinkedInVariant(
            text_post=text_post,
            hashtags=hashtags,
            pdf_carousel_slides=carousel_slides,
            media_s3_keys=media_s3_keys or [],
            specs={
                "max_post_length": 3000,
                "tone": "professional",
                "format": "text_with_pdf_carousel",
                "carousel_max_slides": 10,
                "carousel_dimensions": "1080x1080 or 1080x1350",
                "hashtag_count": "3-5",
            },
        )

        logger.info(
            "linkedin_optimized",
            title=title[:60],
            post_length=len(text_post),
            slides=len(carousel_slides),
        )
        return variant

    def _generate_text_post(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str,
        cta_text: str,
    ) -> str:
        """Generate a text-first LinkedIn post with professional tone."""
        parts: list[str] = []

        # Hook line (first line is crucial for LinkedIn)
        hook = hook_text or title
        parts.append(hook)
        parts.append("")

        # Single-line paragraph style (LinkedIn best practice)
        parts.append("Here's what I've learned:")
        parts.append("")

        for i, point in enumerate(talking_points[:6]):
            # Use numbered format with line breaks
            parts.append(f"{i + 1}. {point}")
            parts.append("")

        # Key takeaway
        if talking_points:
            parts.append("💡 The biggest takeaway?")
            parts.append("")
            parts.append(talking_points[0])
            parts.append("")

        # Discussion question / CTA
        cta = cta_text or "What's your experience with this? I'd love to hear your thoughts. 👇"
        parts.append("—")
        parts.append("")
        parts.append(cta)

        full_post = "\n".join(parts)

        # Truncate if over limit
        if len(full_post) > self.MAX_POST_LENGTH:
            full_post = full_post[: self.MAX_POST_LENGTH - 3] + "..."

        return full_post

    def _generate_hashtags(self, keywords: list[str]) -> list[str]:
        """Generate 3-5 professional hashtags (LinkedIn prefers fewer)."""
        hashtags: list[str] = []

        for kw in keywords[:3]:
            tag = kw.replace(" ", "").lower()
            if len(tag) > 2:
                hashtags.append(f"#{tag}")

        # Add professional generic tags
        professional = ["#leadership", "#growth", "#innovation", "#strategy", "#learning"]
        for tag in professional:
            if tag not in hashtags and len(hashtags) < 5:
                hashtags.append(tag)

        return hashtags[:5]

    def _generate_pdf_carousel(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str,
    ) -> list[dict[str, str]]:
        """Generate PDF carousel slide content."""
        slides: list[dict[str, str]] = []

        # Cover slide
        slides.append({
            "slide_number": "1",
            "type": "cover",
            "headline": hook_text or title,
            "subtext": "A guide for professionals →",
        })

        # Content slides
        for i, point in enumerate(talking_points[:7]):
            slides.append({
                "slide_number": str(i + 2),
                "type": "content",
                "headline": f"Insight #{i + 1}",
                "body": point,
            })

        # Summary slide
        slides.append({
            "slide_number": str(len(slides) + 1),
            "type": "summary",
            "headline": "Key Takeaways",
            "body": "\n".join(f"✓ {tp[:60]}" for tp in talking_points[:4]),
        })

        # CTA slide
        slides.append({
            "slide_number": str(len(slides) + 1),
            "type": "cta",
            "headline": "Found this valuable?",
            "body": "♻️ Repost to help your network\n💾 Save for reference\n🔔 Follow for more insights",
        })

        return slides[:10]
