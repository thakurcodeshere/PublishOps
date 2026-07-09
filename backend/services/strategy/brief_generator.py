"""Brief generator using Claude API to produce structured content briefs."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import anthropic

from backend.config import get_settings
from backend.services.intelligence.scorer import ScoredTopic
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior content strategist for a multi-platform digital media brand.
Your job is to create detailed production briefs that will guide the creation of high-performing content.

Guidelines:
- Write in an authoritative but approachable tone
- Focus on providing genuine value to the audience
- Every piece must have a clear angle that differentiates it from existing content
- Consider the psychology of the target emotion when designing the content flow
- Always include specific, actionable talking points (not vague generalities)
- Design CTAs that feel natural and earned, not forced

Output must be valid JSON with the following structure:
{
  "angle": "The unique perspective or hook for this content",
  "audience": "Primary target audience description",
  "talking_points": ["Point 1", "Point 2", ...],
  "cta_strategy": "Description of the call-to-action approach",
  "platform_variants": [
    {"platform": "youtube", "format": "long_form", "notes": "..."},
    ...
  ],
  "tone_notes": "Specific tone and voice guidance",
  "key_statistics": ["Any relevant stats to include"],
  "potential_controversy": "Any sensitive aspects to be careful about",
  "competitor_gap": "What existing content misses that we can address"
}"""


@dataclass
class ContentBrief:
    """Structured content brief output."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    topic_title: str = ""
    angle: str = ""
    audience: str = ""
    talking_points: list[str] = field(default_factory=list)
    cta_strategy: str = ""
    platform_variants: list[dict[str, str]] = field(default_factory=list)
    tone_notes: str = ""
    key_statistics: list[str] = field(default_factory=list)
    potential_controversy: str = ""
    competitor_gap: str = ""
    target_emotion: str = ""
    hook_text: str = ""
    format: str = ""
    brief_text: str = ""


class BriefGenerator:
    """Generate content briefs using the Claude API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"

    async def generate_brief(
        self,
        scored_topic: ScoredTopic,
        hook_text: str = "",
        emotion: str = "curiosity",
        target_platforms: list[str] | None = None,
    ) -> ContentBrief:
        """Generate a full content brief from a scored topic."""
        platforms = target_platforms or ["youtube", "tiktok", "instagram", "twitter", "linkedin"]

        user_prompt = f"""Create a detailed content production brief for the following topic:

**Topic:** {scored_topic.raw.title}
**Description:** {scored_topic.raw.description}
**Source Platform:** {scored_topic.raw.platform}
**Velocity Score:** {scored_topic.velocity_score}/100
**Evergreen Score:** {scored_topic.evergreen_score}/100
**Platform Fit:** {scored_topic.platform_fit}/100
**Saturation:** {scored_topic.saturation:.2f}

**Hook to use:** {hook_text or 'Generate the best hook for this topic'}
**Target Emotion:** {emotion}
**Target Platforms:** {', '.join(platforms)}
**Number of variants to plan:** {len(platforms) + 1}

Engagement metrics from source:
{json.dumps(scored_topic.raw.engagement_metrics, indent=2)}

Create a comprehensive brief that maximizes engagement across all target platforms.
Respond with ONLY valid JSON."""

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                raw_text = "\n".join(lines[1:-1])

            data: dict[str, Any] = json.loads(raw_text)

            brief = ContentBrief(
                topic_title=scored_topic.raw.title,
                angle=data.get("angle", ""),
                audience=data.get("audience", ""),
                talking_points=data.get("talking_points", []),
                cta_strategy=data.get("cta_strategy", ""),
                platform_variants=data.get("platform_variants", []),
                tone_notes=data.get("tone_notes", ""),
                key_statistics=data.get("key_statistics", []),
                potential_controversy=data.get("potential_controversy", ""),
                competitor_gap=data.get("competitor_gap", ""),
                target_emotion=emotion,
                hook_text=hook_text,
                format=data.get("platform_variants", [{}])[0].get("format", "long_form") if data.get("platform_variants") else "long_form",
                brief_text=raw_text,
            )

            logger.info(
                "brief_generated",
                topic=scored_topic.raw.title,
                variants=len(brief.platform_variants),
                talking_points=len(brief.talking_points),
            )
            return brief

        except json.JSONDecodeError as exc:
            logger.error("brief_json_parse_error", error=str(exc))
            return ContentBrief(
                topic_title=scored_topic.raw.title,
                angle=f"Coverage of: {scored_topic.raw.title}",
                audience="General audience interested in trending topics",
                talking_points=[scored_topic.raw.description],
                cta_strategy="Subscribe and follow for more content",
                platform_variants=[{"platform": p, "format": "standard"} for p in platforms],
                target_emotion=emotion,
                hook_text=hook_text,
                format="standard",
                brief_text=f"Auto-generated brief for: {scored_topic.raw.title}",
            )
        except Exception as exc:
            logger.error("brief_generation_error", error=str(exc), topic=scored_topic.raw.title)
            raise
