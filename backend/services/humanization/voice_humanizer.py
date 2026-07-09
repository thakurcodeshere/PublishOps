"""Voice humanizer — inject SSML breath patterns and micro-pauses."""

from __future__ import annotations

import random
import re

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceHumanizer:
    """Inject natural-sounding SSML pauses and breath patterns into script text."""

    # Pause durations in milliseconds
    SENTENCE_PAUSE_RANGE = (400, 700)
    THOUGHT_PAUSE_RANGE = (200, 500)
    EMPHASIS_PAUSE = 150

    def inject_breath_patterns(self, script_text: str) -> str:
        """
        Add SSML <break> tags at natural speech boundaries.

        - Sentence boundaries: 400-700ms breaks
        - Thought transitions (commas, dashes): 200-500ms micro-pauses
        - Rate variation between sections
        """
        if not script_text.strip():
            return script_text

        # Wrap in <speak> root
        result = self._add_sentence_breaks(script_text)
        result = self._add_thought_pauses(result)
        result = self._add_rate_variation(result)
        result = f'<speak>\n{result}\n</speak>'

        logger.info(
            "voice_humanizer_applied",
            original_len=len(script_text),
            ssml_len=len(result),
        )
        return result

    def _add_sentence_breaks(self, text: str) -> str:
        """Add pauses after sentence-ending punctuation."""
        def _replace_sentence_end(match: re.Match[str]) -> str:
            punct = match.group(1)
            space = match.group(2)
            pause_ms = random.randint(*self.SENTENCE_PAUSE_RANGE)
            return f'{punct}<break time="{pause_ms}ms"/>{space}'

        # Match sentence endings followed by space and uppercase letter
        pattern = r'([.!?])(\s+)(?=[A-Z])'
        return re.sub(pattern, _replace_sentence_end, text)

    def _add_thought_pauses(self, text: str) -> str:
        """Add micro-pauses at thought transitions (commas, semicolons, dashes)."""
        def _replace_comma(match: re.Match[str]) -> str:
            sep = match.group(1)
            space = match.group(2)
            pause_ms = random.randint(*self.THOUGHT_PAUSE_RANGE)
            return f'{sep}<break time="{pause_ms}ms"/>{space}'

        # Match commas, semicolons, em-dashes followed by space
        pattern = r'([,;—–-])(\s+)'
        return re.sub(pattern, _replace_comma, text)

    def _add_rate_variation(self, text: str) -> str:
        """Vary speaking rate slightly between sections to sound more natural."""
        sections = text.split("\n\n")
        if len(sections) <= 1:
            return text

        varied: list[str] = []
        rates = ["95%", "100%", "105%", "98%", "102%"]

        for i, section in enumerate(sections):
            if not section.strip():
                varied.append(section)
                continue

            rate = rates[i % len(rates)]
            if rate != "100%":
                section = f'<prosody rate="{rate}">{section}</prosody>'
            varied.append(section)

        return "\n\n".join(varied)
