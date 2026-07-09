"""Voice synthetics detector service (Tier C) for checking if audio sounds generated/robotic."""

from __future__ import annotations

import io
from typing import Any

import httpx

from backend.config import get_settings

try:
    import librosa
    import numpy as np
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class VoiceDetector:
    """Analyzes audio for synthetic markers and deepfake voices."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _local_acoustic_check(self, audio_data: bytes) -> float:
        """Fallback acoustic analysis for detecting synthetic/TTS signatures.
        
        Synthetic voices often suffer from:
        1. Low spectral flatness variance (too uniform).
        2. Robot-like phase alignment or lack of micro-tremor.
        """
        score = 0.15  # baseline probability

        if HAS_SCIPY:
            try:
                y, sr = librosa.load(io.BytesIO(audio_data), sr=None)
                
                # 1. Spectral Flatness (measure of noise vs tone)
                flatness = librosa.feature.spectral_flatness(y=y)
                flatness_variance = float(np.var(flatness))
                
                # If flatness is extremely consistent (low variance), it's likely synthetic
                if flatness_variance < 0.0005:
                    score += 0.35
                elif flatness_variance > 0.002:
                    score -= 0.05

                # 2. Pitch micro-tremor (humans have organic drift, AI is often too perfect)
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
                valid_pitches = pitches[magnitudes > 0.1]
                actual_pitches = valid_pitches[(valid_pitches > 50) & (valid_pitches < 350)]
                if len(actual_pitches) > 5:
                    pitch_var = float(np.var(actual_pitches))
                    if pitch_var < 1.0:  # extremely steady pitch (robotic)
                        score += 0.3
                    elif pitch_var > 15.0:
                        score -= 0.1

            except Exception:
                pass
                
        # Return bounded probability
        return max(0.05, min(0.95, score))

    async def detect_synthetic_voice(self, audio_data: bytes) -> float:
        """Call synthetic voice detectors or use local acoustic checks.
        
        Returns a float between 0.0 and 1.0.
        """
        resemble_detect_key = getattr(self.settings, "RESEMBLE_DETECT_API_KEY", "") or "mock"
        
        if resemble_detect_key and resemble_detect_key != "mock":
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    response = await client.post(
                        "https://detect.resemble.ai/api/v1/detect",
                        headers={"Authorization": f"Token token={resemble_detect_key}"},
                        files={"file": ("voice.wav", audio_data, "audio/wav")}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return float(data.get("score", 0.5))
            except Exception:
                pass

        return self._local_acoustic_check(audio_data)
