"""Adversarial Red-Team orchestrator service (Tier C) for checking if content passes as human-made."""

from __future__ import annotations

import logging
from typing import Any

from backend.services.redteam.cadence_checker import CadenceChecker
from backend.services.redteam.text_detector import TextDetector
from backend.services.redteam.visual_detector import VisualDetector
from backend.services.redteam.voice_detector import VoiceDetector

logger = logging.getLogger(__name__)


class RedTeamOrchestrator:
    """Orchestrates multi-channel adversarial verification tests on produced content."""

    def __init__(self) -> None:
        self.text_detector = TextDetector()
        self.voice_detector = VoiceDetector()
        self.visual_detector = VisualDetector()
        self.cadence_checker = CadenceChecker()

    async def test_content(
        self,
        text_content: str | None = None,
        audio_data: bytes | None = None,
        video_data: bytes | None = None,
        creator_profile: Any | None = None,
    ) -> dict[str, Any]:
        """Verify script, audio, and video against the adversarial detection suite.
        
        Returns:
            A dictionary containing:
            - passed (bool): True if composite score < 0.30
            - composite_score (float): Max AI probability detected across active channels
            - scores (dict[str, float]): Individual channel scores
            - failing_channels (list[str]): Channels exceeding the threshold
        """
        scores: dict[str, float] = {}
        failing_channels: list[str] = []

        # 1. Test Text/Script
        if text_content:
            try:
                txt_score = await self.text_detector.detect_ai_probability(text_content)
                scores["text"] = round(txt_score, 3)
                if txt_score >= 0.30:
                    failing_channels.append("text")
            except Exception as e:
                logger.error(f"Error running text red-team detector: {e}")
                scores["text"] = 0.5  # suspect fallback

        # 2. Test Audio (Voice & Cadence)
        if audio_data:
            # Voice Synthetics detector
            try:
                voice_score = await self.voice_detector.detect_synthetic_voice(audio_data)
                scores["voice_synthetic"] = round(voice_score, 3)
                if voice_score >= 0.30:
                    failing_channels.append("voice_synthetic")
            except Exception as e:
                logger.error(f"Error running voice synthetic detector: {e}")
                scores["voice_synthetic"] = 0.5

            # Cadence variance checker
            if creator_profile and hasattr(creator_profile, "cadence") and creator_profile.cadence:
                try:
                    cadence_profile_dict = creator_profile.cadence.profile_data
                    cadence_score = self.cadence_checker.verify_cadence(audio_data, cadence_profile_dict)
                    scores["voice_cadence"] = round(cadence_score, 3)
                    if cadence_score >= 0.30:
                        failing_channels.append("voice_cadence")
                except Exception as e:
                    logger.error(f"Error running cadence checker: {e}")
                    scores["voice_cadence"] = 0.5
            else:
                # Default baseline profile fallback if creator not calibrated
                try:
                    default_profile = {
                        "wpm_mean": 150.0,
                        "average_pause_length_secs": 0.35
                    }
                    cadence_score = self.cadence_checker.verify_cadence(audio_data, default_profile)
                    scores["voice_cadence"] = round(cadence_score, 3)
                    if cadence_score >= 0.30:
                        failing_channels.append("voice_cadence")
                except Exception as e:
                    logger.error(f"Error running default cadence checker: {e}")
                    scores["voice_cadence"] = 0.5

        # 3. Test Visuals (deepfake/AI check)
        if video_data:
            try:
                visual_score = await self.visual_detector.detect_synthetic_visuals(video_data)
                scores["visual_synthetic"] = round(visual_score, 3)
                # Visual Deepfake detection threshold is also 0.30
                if visual_score >= 0.30:
                    failing_channels.append("visual_synthetic")
            except Exception as e:
                logger.error(f"Error running visual detector: {e}")
                scores["visual_synthetic"] = 0.5

        if not scores:
            return {
                "passed": True,
                "composite_score": 0.0,
                "scores": {},
                "failing_channels": []
            }

        # Composite score is the maximum probability across channels (strongest signal of AI)
        composite_score = max(scores.values())
        passed = composite_score < 0.30

        return {
            "passed": passed,
            "composite_score": round(composite_score, 3),
            "scores": scores,
            "failing_channels": failing_channels
        }
