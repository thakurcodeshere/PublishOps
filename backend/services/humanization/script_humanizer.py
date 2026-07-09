"""Script humanizer — second Claude pass for conversational polish."""

from __future__ import annotations

import anthropic

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a script editor specializing in making AI-generated scripts sound human.

Your job:
1. Replace stiff/corporate phrasing with conversational language
2. Add natural speech patterns: filler words (sparingly), self-corrections, parenthetical asides
3. Inject first-person micro-stories where appropriate (use the story bank provided)
4. Remove phrases that sound AI-generated:
   - "In today's video..."
   - "Let's dive in..."
   - "Without further ado..."
   - "It's important to note..."
   - "In conclusion..."
   - "As you can see..."
   - "Buckle up..."
   - "Game-changer"
   - "At the end of the day"
5. Make transitions feel like natural thought progression, not structured segments
6. Vary sentence length dramatically (mix 3-word punches with longer explanations)

RULES:
- Keep the same information and structure
- Don't change the [HOOK], [BODY], [CTA] markers
- Don't add new information
- Maintain the emotional target
- Output ONLY the revised script text"""


STORY_BANK = [
    "I remember when I first learned about this — I was literally sitting in a coffee shop, and it completely changed how I thought about everything.",
    "A friend of mine tried this last month, and the results genuinely surprised both of us.",
    "I've been thinking about this a lot lately, and here's what I keep coming back to.",
    "When I first heard about this, I was honestly skeptical. But then I looked at the data.",
    "Someone in my community asked me about this recently, and I realized I needed to dig deeper.",
    "I spent way too long researching this, but I think I finally get why it matters.",
]


class ScriptHumanizer:
    """Humanize AI-generated scripts using a second Claude pass."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"

    async def humanize_script(self, script_text: str, target_emotion: str = "curiosity") -> str:
        """
        Run a second Claude pass to make the script more conversational.

        Removes AI-sounding phrases, adds natural speech patterns, and
        injects first-person story elements.
        """
        if not script_text.strip():
            return script_text

        user_prompt = f"""Humanize this script. Target emotion: {target_emotion}

Story bank (use 1-2 naturally if appropriate):
{chr(10).join(f'- {s}' for s in STORY_BANK)}

SCRIPT TO HUMANIZE:
---
{script_text}
---

Return ONLY the humanized script text. No explanations."""

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            humanized = response.content[0].text.strip()

            # Verify we didn't lose the section markers
            if "[HOOK]" not in humanized and "[HOOK]" in script_text:
                logger.warning("humanizer_lost_markers_using_original")
                return script_text

            logger.info(
                "script_humanized",
                original_len=len(script_text),
                humanized_len=len(humanized),
                length_change=len(humanized) - len(script_text),
            )
            return humanized

        except Exception as exc:
            logger.error("script_humanization_error", error=str(exc))
            return script_text  # Return original on failure
