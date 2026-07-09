"""Script writer using Claude API — platform-specific scripts with A/B variants."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import anthropic

from backend.config import get_settings
from backend.services.strategy.brief_generator import ContentBrief
from backend.utils.logger import get_logger
from backend.services.fingerprint.opinion_store import OpinionStore
from backend.services.intelligence.vocab_miner import AudienceVocabularyMiner
from backend.models.creator_profile import CreatorProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

logger = get_logger(__name__)

PLATFORM_TEMPLATES: dict[str, dict[str, Any]] = {
    "youtube": {
        "duration_range": "8-12 minutes",
        "structure": "Hook (0:00-0:30) → Context (0:30-2:00) → Body with 3-5 key points → CTA (last 30s)",
        "notes": "Front-load value. Pattern interrupt every 60-90s. Use timestamps for chapters.",
    },
    "tiktok": {
        "duration_range": "30-90 seconds",
        "structure": "Hook (0-3s) → Core value (3-60s) → CTA (last 5s)",
        "notes": "Immediate hook. Fast pacing. No wasted frames. End with a loop-friendly transition.",
    },
    "instagram": {
        "duration_range": "60-90 seconds for Reels, 10 slides for Carousel",
        "structure": "Visual hook → Value delivery → Save prompt",
        "notes": "Visual-first. Text overlays required. Caption complements, doesn't repeat.",
    },
    "twitter": {
        "duration_range": "Thread of 5-10 tweets, ≤280 chars each",
        "structure": "Hook tweet → Value tweets → Recap → CTA",
        "notes": "Each tweet must stand alone. Use numbered format. End with engagement question.",
    },
    "linkedin": {
        "duration_range": "1500-2000 characters",
        "structure": "Hook line → Story/insight → Key takeaways → Discussion question",
        "notes": "Professional tone. First-person narrative. Single-line paragraphs. No hashtags in body.",
    },
}

BASE_SYSTEM_PROMPT = """You are an expert scriptwriter for multi-platform content.
Write scripts that are engaging, conversational, and optimised for the target platform.

RULES:
- Use [HOOK], [BODY], and [CTA] section markers with timestamps
- Write in a natural, human voice — avoid corporate speak
- Include pattern interrupts and engagement hooks throughout
- Every sentence must earn its place — cut anything that doesn't add value
- Include specific examples, numbers, and concrete references
- Write two variants: A (primary) and B (alternative angle)

Output as valid JSON:
{
  "variant_a": {
    "hook": "...",
    "body": "...",
    "cta": "...",
    "estimated_duration_seconds": 480,
    "word_count": 1200,
    "timestamps": ["0:00 - Hook", "0:30 - Context", ...]
  },
  "variant_b": {
    "hook": "...",
    "body": "...",
    "cta": "...",
    "estimated_duration_seconds": 480,
    "word_count": 1200,
    "timestamps": ["0:00 - Hook", "0:30 - Context", ...]
  }
}"""


@dataclass
class Script:
    """A generated script with A/B variants."""

    variant_a: dict[str, Any] = field(default_factory=dict)
    variant_b: dict[str, Any] = field(default_factory=dict)
    platform: str = ""
    full_text_a: str = ""
    full_text_b: str = ""


class ScriptWriter:
    """Generate platform-specific scripts using the Claude API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"
        self.opinion_store = OpinionStore()
        self.vocab_miner = AudienceVocabularyMiner()

    async def generate_script(
        self,
        brief: ContentBrief,
        platform: str,
        db: AsyncSession | None = None,
        creator_id: uuid.UUID | None = None
    ) -> Script:
        """Generate a platform-specific script with A/B variants."""
        template = PLATFORM_TEMPLATES.get(platform.lower(), PLATFORM_TEMPLATES["youtube"])

        # Compile custom persona and RAG rules if calibration is active
        custom_rules = []
        if db and creator_id:
            # 1. Fetch Creator Profile for lexical styling
            creator_res = await db.execute(
                select(CreatorProfile).where(CreatorProfile.id == creator_id)
            )
            creator = creator_res.scalar_one_or_none()
            if creator and creator.lexical:
                lex = creator.lexical.profile_data
                custom_rules.append("### WRITING STYLE CONSTRAINTS (LEXICAL CHANNEL)")
                custom_rules.append(f"- Target Readability Index: Flesch-Kincaid grade around {lex.get('readability_score', 65.0)}")
                custom_rules.append(f"- Contractions Usage: Maintain a contractions ratio of {lex.get('contractions_ratio', 0.05)}")
                custom_rules.append(f"- Sentence Lengths: Aim for an average sentence length of {lex.get('average_sentence_length', 12.0)} words.")
                
                dist = lex.get("sentence_length_distribution", {})
                if dist:
                    custom_rules.append(f"  * Keep sentence lengths mixed: {dist.get('short', 30)}% short (<8 words), {dist.get('medium', 40)}% medium, {dist.get('long', 20)}% long.")
                custom_rules.append("")

            # 2. Fetch Voice Bible Opinion constraints
            opinions_prompt = await self.opinion_store.get_voice_bible_prompt_constraints(db, creator_id)
            if opinions_prompt:
                custom_rules.append(opinions_prompt)
                custom_rules.append("")

            # 3. Fetch Mined Vocabulary RAG Context
            vocab_prompt = await self.vocab_miner.get_rag_context_for_script(db, brief.topic_title)
            if vocab_prompt:
                custom_rules.append(vocab_prompt)
                custom_rules.append("")

        custom_system_prompt = BASE_SYSTEM_PROMPT
        if custom_rules:
            custom_system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + "\n".join(custom_rules)

        user_prompt = f"""Write a {platform.upper()} script for the following content brief:

**Topic:** {brief.topic_title}
**Angle:** {brief.angle}
**Target Emotion:** {brief.target_emotion}
**Hook:** {brief.hook_text}
**Audience:** {brief.audience}

**Talking Points:**
{chr(10).join(f'- {tp}' for tp in brief.talking_points)}

**CTA Strategy:** {brief.cta_strategy}
**Tone Notes:** {brief.tone_notes}

**Platform Requirements:**
- Duration: {template['duration_range']}
- Structure: {template['structure']}
- Notes: {template['notes']}

Write two distinct variants (A and B) with different hooks and angles.
Respond with ONLY valid JSON."""

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4000,
                system=custom_system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                raw_text = "\n".join(lines[1:-1])

            data: dict[str, Any] = json.loads(raw_text)

            variant_a = data.get("variant_a", {})
            variant_b = data.get("variant_b", {})

            script = Script(
                variant_a=variant_a,
                variant_b=variant_b,
                platform=platform,
                full_text_a=f"[HOOK]\n{variant_a.get('hook', '')}\n\n[BODY]\n{variant_a.get('body', '')}\n\n[CTA]\n{variant_a.get('cta', '')}",
                full_text_b=f"[HOOK]\n{variant_b.get('hook', '')}\n\n[BODY]\n{variant_b.get('body', '')}\n\n[CTA]\n{variant_b.get('cta', '')}",
            )

            logger.info(
                "script_generated",
                platform=platform,
                topic=brief.topic_title[:60],
                word_count_a=variant_a.get("word_count", 0),
                word_count_b=variant_b.get("word_count", 0),
            )
            return script

        except json.JSONDecodeError as exc:
            logger.error("script_json_parse_error", error=str(exc))
            fallback_text = f"[HOOK]\n{brief.hook_text}\n\n[BODY]\n{brief.angle}. " + " ".join(brief.talking_points) + f"\n\n[CTA]\n{brief.cta_strategy}"
            return Script(
                variant_a={"hook": brief.hook_text, "body": brief.angle, "cta": brief.cta_strategy},
                variant_b={"hook": brief.hook_text, "body": brief.angle, "cta": brief.cta_strategy},
                platform=platform,
                full_text_a=fallback_text,
                full_text_b=fallback_text,
            )
        except Exception as exc:
            logger.error("script_generation_error", error=str(exc))
            raise
