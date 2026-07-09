"""Disfluency calibrator service (Tier C) to measure stumble rates and inject natural verbal disfluencies."""

from __future__ import annotations

import random
import re
from typing import Any

# Default filler particles for synthetic disfluencies
STANDARD_DISFLUENCIES = ["uh", "um", "ah", "err"]


class DisfluencyCalibrator:
    """Measures natural stumble/filler rate and inserts them back into scripts for humanization."""

    def analyze_transcripts(self, raw_audio_transcript: str, cleaned_script: str) -> dict[str, Any]:
        """Compare the actual speech transcription against the structured clean script to count stumbles.
        
        Args:
            raw_audio_transcript: What was actually spoken (includes 'uh', 'um', stumbles).
            cleaned_script: The base script written beforehand.
            
        Returns:
            A disfluency profile dict.
        """
        raw_words = re.findall(r"\b[a-zA-Z']+\b", raw_audio_transcript.lower())
        clean_words = re.findall(r"\b[a-zA-Z']+\b", cleaned_script.lower())
        
        raw_len = len(raw_words)
        clean_len = len(clean_words)
        
        # 1. Identify filler count
        filler_count = 0
        fillers_detected: dict[str, int] = {}
        for w in raw_words:
            if w in STANDARD_DISFLUENCIES:
                filler_count += 1
                fillers_detected[w] = fillers_detected.get(w, 0) + 1

        # 2. Count repetitions (e.g. "the the", "I I've")
        repetition_count = 0
        for i in range(len(raw_words) - 1):
            if raw_words[i] == raw_words[i + 1] and raw_words[i] not in STANDARD_DISFLUENCIES:
                repetition_count += 1

        # Estimate duration assuming 140 WPM if not provided
        estimated_duration_min = max(1, clean_len) / 140.0
        
        total_stumbles = filler_count + repetition_count
        stumbles_per_min = total_stumbles / estimated_duration_min

        # Keep within a natural 2.0 - 4.0 range for humanization targets
        target_stumbles_per_min = max(1.5, min(4.5, stumbles_per_min))

        return {
            "filler_count": filler_count,
            "repetition_count": repetition_count,
            "stumbles_per_minute": round(stumbles_per_min, 2),
            "target_stumbles_per_minute": round(target_stumbles_per_min, 2),
            "preferred_fillers": fillers_detected or {"um": 3, "uh": 2},
            "repetition_ratio": round(repetition_count / max(1, raw_len), 4)
        }

    def inject_disfluencies(self, clean_script: str, profile: dict[str, Any]) -> str:
        """Inject mild, natural verbal disfluencies and punctuation pauses into a script.
        
        Enforces the target stumbles/min (usually 2-4) at logical clause/sentence boundaries.
        """
        words = clean_script.split()
        word_count = len(words)
        
        # Determine how many disfluencies to inject
        target_rate = profile.get("target_stumbles_per_minute", 2.5)
        # Assume average speech speed of 150 WPM to determine count
        estimated_minutes = word_count / 150.0
        num_to_inject = max(1, int(estimated_minutes * target_rate))

        # Get list of preferred fillers
        preferred_fillers = list(profile.get("preferred_fillers", {"um": 1}).keys())
        if not preferred_fillers:
            preferred_fillers = STANDARD_DISFLUENCIES

        # Find comma and sentence boundaries for natural placements
        sentences = [s.strip() for s in re.split(r"([.!?,\n]+)", clean_script) if s.strip()]
        
        # Reconstruct with disfluencies injected at boundary punctuations
        injected_indices = set()
        
        # Select random indices among comma/period separators (odd indices in sentences if splitting by pattern with group)
        eligible_indices = [i for i, part in enumerate(sentences) if part in [".", "?", "!", ",", "\n"]]
        
        if eligible_indices:
            num_to_inject = min(num_to_inject, len(eligible_indices))
            injected_indices = set(random.sample(eligible_indices, num_to_inject))

        result = []
        for i, part in enumerate(sentences):
            result.append(part)
            if i in injected_indices:
                filler = random.choice(preferred_fillers)
                # Randomize format: " [filler]..." or " [filler],"
                if part == "," or part == "\n":
                    result.append(f" {filler},")
                else:
                    result.append(f" {filler}...")

        # Flatten and clean up whitespace
        final_script = "".join(result)
        final_script = re.sub(r"\s+", " ", final_script).strip()
        
        # Clean double punctuations like "... ." or ",..."
        final_script = re.sub(r"\.\.\.\s*\.", "...", final_script)
        final_script = re.sub(r",\s*,", ",", final_script)
        final_script = re.sub(r",\s*\.\.\.", "...", final_script)

        return final_script
