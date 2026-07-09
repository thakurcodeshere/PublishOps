"""Emotion mapper — maps topic characteristics to optimal target emotions."""

from __future__ import annotations

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Emotion definitions and when they work best
EMOTIONS = {
    "curiosity": {
        "signals": ["what", "how", "why", "secret", "hidden", "unknown", "mystery", "surprising", "revealed"],
        "platforms": {"youtube": 0.9, "tiktok": 0.8, "instagram": 0.7, "twitter": 0.7, "linkedin": 0.8},
        "description": "Drives clicks and watch time through information gaps",
    },
    "fomo": {
        "signals": ["trending", "everyone", "viral", "millions", "don't miss", "limited", "exclusive", "before"],
        "platforms": {"youtube": 0.7, "tiktok": 0.9, "instagram": 0.9, "twitter": 0.8, "linkedin": 0.5},
        "description": "Creates urgency through social proof and scarcity",
    },
    "urgency": {
        "signals": ["breaking", "now", "urgent", "warning", "alert", "immediately", "deadline", "today"],
        "platforms": {"youtube": 0.6, "tiktok": 0.7, "instagram": 0.6, "twitter": 0.9, "linkedin": 0.6},
        "description": "Demands immediate attention for time-sensitive content",
    },
    "inspiration": {
        "signals": ["success", "achieve", "transform", "journey", "dream", "possible", "growth", "incredible"],
        "platforms": {"youtube": 0.8, "tiktok": 0.7, "instagram": 0.9, "twitter": 0.6, "linkedin": 0.9},
        "description": "Motivates through aspirational stories and outcomes",
    },
    "outrage": {
        "signals": ["scandal", "exposed", "lie", "fraud", "corrupt", "unfair", "wrong", "controversial"],
        "platforms": {"youtube": 0.8, "tiktok": 0.8, "instagram": 0.5, "twitter": 0.9, "linkedin": 0.4},
        "description": "Drives engagement through moral indignation",
    },
    "amusement": {
        "signals": ["funny", "hilarious", "meme", "comedy", "joke", "lol", "humor", "ridiculous"],
        "platforms": {"youtube": 0.7, "tiktok": 0.9, "instagram": 0.8, "twitter": 0.8, "linkedin": 0.3},
        "description": "Drives shares through entertainment value",
    },
}


class EmotionMapper:
    """Map topic characteristics to optimal target emotions per platform."""

    def _score_emotion(self, text: str, emotion: str, platform: str) -> float:
        """Score how well an emotion fits the topic for a given platform."""
        emotion_data = EMOTIONS.get(emotion, {})
        signals: list[str] = emotion_data.get("signals", [])
        platform_weights: dict[str, float] = emotion_data.get("platforms", {})

        text_lower = text.lower()

        # Count matching signals
        signal_matches = sum(1 for s in signals if s in text_lower)
        signal_score = min(signal_matches / max(len(signals), 1), 1.0)

        # Platform fit
        platform_score = platform_weights.get(platform.lower(), 0.5)

        # Combined score
        return (signal_score * 0.6) + (platform_score * 0.4)

    def map_emotion(self, topic_title: str, platform: str, topic_description: str = "") -> str:
        """
        Map a topic to its optimal target emotion for a given platform.

        Analyses topic keywords against emotion signal patterns and
        platform-specific emotional effectiveness.
        """
        combined_text = f"{topic_title} {topic_description}"

        scores: dict[str, float] = {}
        for emotion in EMOTIONS:
            scores[emotion] = self._score_emotion(combined_text, emotion, platform)

        best_emotion = max(scores, key=scores.get)  # type: ignore[arg-type]

        # If no strong signal, default to curiosity (safest general-purpose emotion)
        if scores[best_emotion] < 0.15:
            best_emotion = "curiosity"

        logger.info(
            "emotion_mapped",
            topic=topic_title[:60],
            platform=platform,
            emotion=best_emotion,
            score=scores[best_emotion],
        )
        return best_emotion

    def get_all_scores(self, topic_title: str, platform: str, topic_description: str = "") -> dict[str, float]:
        """Return scores for all emotions for analysis/debugging."""
        combined_text = f"{topic_title} {topic_description}"
        return {
            emotion: round(self._score_emotion(combined_text, emotion, platform), 3)
            for emotion in EMOTIONS
        }
