"""Text AI Detector client (Tier C) for adversarial analysis on scripts."""

from __future__ import annotations

import httpx
from backend.config import get_settings

# Classic AI words and phrases
AI_CLICHES = [
    "delve", "tapestry", "testament", "beacon", "revolutionize",
    "foster", "impactful", "moreover", "furthermore", "in conclusion",
    "it is important to note", "not only... but also", "journey", "key to",
    "vital", "crucial", "essential", "dynamic"
]

class TextDetector:
    """Classifies text/script to detect AI-generated traits using external APIs and local heuristics."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _local_heuristic_score(self, text: str) -> float:
        """Analyze text local style features to estimate AI probability (fallback).
        
        Returns a score from 0.0 (fully human) to 1.0 (fully AI).
        """
        text_lower = text.lower()
        words = text_lower.split()
        if not words:
            return 0.0

        score = 0.1  # base score

        # 1. Count AI clichés
        cliche_count = sum(text_lower.count(cliche) for cliche in AI_CLICHES)
        cliche_ratio = cliche_count / (len(words) / 100.0) # clichés per 100 words
        score += min(0.4, cliche_ratio * 0.15)

        # 2. Check for sentence length uniformity (AI tends to have very uniform length)
        # Split into sentences
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if len(sentences) > 3:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            # Low variance in sentence length is typical for simple AI writing
            if variance < 8.0:
                score += 0.2
            elif variance > 25.0:
                score -= 0.1  # human writing varies more

        # 3. Pronoun distribution
        # AI often overuse passive voice or formal "we"/"it" over conversational "I"/"you"
        i_count = words.count("i") + words.count("my") + words.count("me")
        you_count = words.count("you") + words.count("your")
        conversational_count = i_count + you_count
        conversational_ratio = conversational_count / len(words)
        
        if conversational_ratio < 0.03:
            score += 0.15
        elif conversational_ratio > 0.08:
            score -= 0.1

        # Keep bounded
        return max(0.05, min(0.95, score))

    async def detect_ai_probability(self, text: str) -> float:
        """Get AI-generated probability score from external services or fallback heuristic.
        
        Returns a float between 0.0 and 1.0.
        """
        # If API keys are available, try external services
        # 1. GPTZero API
        if self.settings.TWITTER_BEARER_TOKEN: # Mocked condition for testing, check for API key
            gptzero_api_key = getattr(self.settings, "GPTZERO_API_KEY", "") or "mock"
            if gptzero_api_key and gptzero_api_key != "mock":
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.post(
                            "https://api.gptzero.me/v2/predict/text",
                            headers={"x-api-key": gptzero_api_key},
                            json={"document": text, "version": "2024-01-09"}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            # Extracts composite AI score
                            return float(data.get("documents", [{}])[0].get("completely_generated", 0.5))
                except Exception:
                    pass

        # Fallback to local heuristics
        return self._local_heuristic_score(text)
