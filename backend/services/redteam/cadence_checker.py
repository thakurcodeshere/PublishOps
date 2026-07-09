"""Cadence checker service (Tier C) for verifying natural variation in speech rate."""

from __future__ import annotations

from typing import Any

from backend.services.fingerprint.cadence_analyzer import CadenceAnalyzer


class CadenceChecker:
    """Verifies that the generated/rendered audio is not metronomic and matches the creator's signature."""

    def __init__(self) -> None:
        self.analyzer = CadenceAnalyzer()

    def verify_cadence(self, rendered_audio: bytes, creator_cadence_profile: dict[str, Any]) -> float:
        """Compare rendered audio's speech cadence metrics against the creator's profile.
        
        Returns a score from 0.0 (perfectly natural matching cadence) to 1.0 (robotic or non-matching).
        """
        # Analyze the rendered audio
        try:
            rendered_metrics = self.analyzer.analyze_audio(rendered_audio)
        except Exception:
            # Fallback to suspicious score if analysis fails
            return 0.5

        ai_probability = 0.1

        # 1. Check WPM variance (robotic voice has low variance)
        rendered_var = rendered_metrics.get("wpm_variance", 0.0)
        
        # If variance is less than 3.0 WPM, it is highly metronomic/robotic
        if rendered_var < 3.0:
            ai_probability += 0.50
        elif rendered_var < 8.0:
            ai_probability += 0.25

        # 2. Check WPM deviation from creator's mean
        creator_mean_wpm = creator_cadence_profile.get("wpm_mean", 150.0)
        rendered_mean_wpm = rendered_metrics.get("wpm_mean", 150.0)
        
        wpm_difference = abs(rendered_mean_wpm - creator_mean_wpm)
        if wpm_difference > 35.0:
            # Speaking rate doesn't match the creator's typical signature at all
            ai_probability += 0.30
        elif wpm_difference > 15.0:
            ai_probability += 0.15

        # 3. Check pause length consistency
        # Humans have varying pause lengths; AI models might have exactly same pause lengths
        avg_pause_sec = rendered_metrics.get("average_pause_length_secs", 0.35)
        creator_avg_pause = creator_cadence_profile.get("average_pause_length_secs", 0.35)
        
        if abs(avg_pause_sec - creator_avg_pause) > 0.25:
            # Pauses are too long or too short compared to the profile
            ai_probability += 0.15

        # Bounded between 0.05 and 0.95
        return max(0.05, min(0.95, ai_probability))
