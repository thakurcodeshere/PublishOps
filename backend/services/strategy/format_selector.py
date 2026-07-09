"""Format selector — decision matrix for optimal content format per platform."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Decision matrix: topic_type × platform → optimal formats (ordered by preference)
_FORMAT_MATRIX: dict[str, dict[str, list[str]]] = {
    "educational": {
        "youtube": ["long_form", "explainer", "tutorial"],
        "tiktok": ["quick_tip", "mini_tutorial", "stitch_reply"],
        "instagram": ["carousel", "reel", "infographic"],
        "twitter": ["thread", "single_tweet"],
        "linkedin": ["article", "pdf_carousel", "text_post"],
    },
    "news": {
        "youtube": ["news_analysis", "commentary", "reaction"],
        "tiktok": ["hot_take", "reaction", "news_clip"],
        "instagram": ["reel", "story_series", "single_image"],
        "twitter": ["thread", "quote_tweet", "single_tweet"],
        "linkedin": ["text_post", "article"],
    },
    "entertainment": {
        "youtube": ["reaction", "commentary", "compilation"],
        "tiktok": ["duet", "trend_response", "skit"],
        "instagram": ["reel", "carousel", "story_series"],
        "twitter": ["single_tweet", "quote_tweet"],
        "linkedin": ["text_post"],
    },
    "opinion": {
        "youtube": ["commentary", "rant", "debate"],
        "tiktok": ["hot_take", "greenscreen", "stitch_reply"],
        "instagram": ["reel", "carousel"],
        "twitter": ["thread", "single_tweet"],
        "linkedin": ["text_post", "article"],
    },
    "tutorial": {
        "youtube": ["tutorial", "walkthrough", "step_by_step"],
        "tiktok": ["mini_tutorial", "quick_tip"],
        "instagram": ["carousel", "reel"],
        "twitter": ["thread"],
        "linkedin": ["pdf_carousel", "article"],
    },
    "trending": {
        "youtube": ["reaction", "commentary", "news_analysis"],
        "tiktok": ["trend_response", "hot_take", "reaction"],
        "instagram": ["reel", "story_series"],
        "twitter": ["single_tweet", "thread"],
        "linkedin": ["text_post"],
    },
}

# Keywords that map to topic types
_TOPIC_TYPE_SIGNALS: dict[str, list[str]] = {
    "educational": ["how to", "guide", "explained", "learn", "what is", "tutorial", "101"],
    "news": ["breaking", "just in", "announced", "launches", "reports", "update"],
    "entertainment": ["funny", "meme", "viral", "reaction", "fails", "comedy"],
    "opinion": ["think", "believe", "should", "hot take", "unpopular opinion", "controversial"],
    "tutorial": ["step by step", "walkthrough", "setup", "install", "configure", "build"],
    "trending": ["trending", "popular", "everyone", "gone viral", "blowing up"],
}


class FormatSelector:
    """Select optimal content format based on topic type and platform."""

    def __init__(self) -> None:
        self._recent_formats: list[str] = []
        self._max_history = 20

    def _detect_topic_type(self, topic_title: str, topic_description: str) -> str:
        """Detect topic type from title and description keywords."""
        combined = f"{topic_title} {topic_description}".lower()
        scores: dict[str, int] = {}

        for topic_type, signals in _TOPIC_TYPE_SIGNALS.items():
            score = sum(1 for s in signals if s in combined)
            if score > 0:
                scores[topic_type] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return "trending"  # Default

    def _check_calendar_balance(self, format_choice: str) -> bool:
        """Check if this format would create a streak (>3 in a row)."""
        if len(self._recent_formats) < 3:
            return True
        last_three = self._recent_formats[-3:]
        return not all(f == format_choice for f in last_three)

    def select_format(
        self,
        topic_title: str,
        platform: str,
        topic_description: str = "",
        historical_performance: dict[str, float] | None = None,
    ) -> str:
        """
        Select the optimal format for a topic on a given platform.

        Considers topic type, platform best practices, historical performance,
        and content calendar balance to avoid format streaks.
        """
        topic_type = self._detect_topic_type(topic_title, topic_description)
        platform_lower = platform.lower()

        # Get format candidates from the matrix
        type_formats = _FORMAT_MATRIX.get(topic_type, _FORMAT_MATRIX["trending"])
        candidates = type_formats.get(platform_lower, ["standard"])

        if not candidates:
            candidates = ["standard"]

        # Apply historical performance weighting if available
        if historical_performance:
            weighted_candidates: list[tuple[str, float]] = []
            for fmt in candidates:
                perf = historical_performance.get(fmt, 0.5)
                weighted_candidates.append((fmt, perf))
            weighted_candidates.sort(key=lambda x: x[1], reverse=True)
            candidates = [wc[0] for wc in weighted_candidates]

        # Pick the best candidate that doesn't break calendar balance
        selected = candidates[0]
        for candidate in candidates:
            if self._check_calendar_balance(candidate):
                selected = candidate
                break

        # Track selection
        self._recent_formats.append(selected)
        if len(self._recent_formats) > self._max_history:
            self._recent_formats = self._recent_formats[-self._max_history:]

        logger.info(
            "format_selected",
            topic_type=topic_type,
            platform=platform,
            format=selected,
        )
        return selected

    def get_format_distribution(self) -> dict[str, int]:
        """Return distribution of recently selected formats."""
        return dict(Counter(self._recent_formats))
