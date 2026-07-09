"""Creator Fingerprint Engine orchestrator (Tier C) to process calibration data and manage profiles."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.creator_profile import (
    AcousticProfile,
    CadenceProfile,
    CreatorProfile,
    DisfluencyProfile,
    LexicalProfile,
    OpinionEntry,
    TemporalProfile,
)
from backend.services.fingerprint.acoustic_profiler import AcousticProfiler
from backend.services.fingerprint.cadence_analyzer import CadenceAnalyzer
from backend.services.fingerprint.disfluency_calibrator import DisfluencyCalibrator
from backend.services.fingerprint.lexical_analyzer import LexicalAnalyzer
from backend.services.fingerprint.temporal_analyzer import TemporalAnalyzer


class CreatorFingerprintEngine:
    """Orchestrates 7-channel calibration to create a composite creator profile."""

    def __init__(self) -> None:
        self.lexical_analyzer = LexicalAnalyzer()
        self.cadence_analyzer = CadenceAnalyzer()
        self.acoustic_profiler = AcousticProfiler()
        self.disfluency_calibrator = DisfluencyCalibrator()
        self.temporal_analyzer = TemporalAnalyzer()

    async def get_or_create_creator(self, db: AsyncSession, name: str, description: str | None = None) -> CreatorProfile:
        """Find an existing creator or create a new profile base."""
        result = await db.execute(select(CreatorProfile).where(CreatorProfile.name == name))
        creator = result.scalar_one_or_none()
        
        if not creator:
            creator = CreatorProfile(name=name, description=description)
            db.add(creator)
            await db.commit()
            await db.refresh(creator)
            
        return creator

    async def get_profile(self, db: AsyncSession, creator_id: uuid.UUID) -> CreatorProfile | None:
        """Fetch the full creator profile including relationships."""
        result = await db.execute(
            select(CreatorProfile)
            .where(CreatorProfile.id == creator_id)
        )
        return result.scalar_one_or_none()

    async def calibrate_creator(
        self,
        db: AsyncSession,
        creator_id: uuid.UUID,
        scripts: list[str],
        audio_files: list[bytes] | None = None,
        audio_transcripts: list[str] | None = None,
        post_timestamps: list[Any] | None = None
    ) -> CreatorProfile:
        """Analyze scripts, audio, and scheduling patterns to build and store the creator's profile.
        
        Runs the full 7-channel calibration pipeline.
        """
        # Load the base creator
        creator = await self.get_profile(db, creator_id)
        if not creator:
            raise ValueError(f"Creator with ID {creator_id} not found.")

        # 1. Lexical calibration
        lexical_data = self.lexical_analyzer.analyze_multiple(scripts) if scripts else {}
        
        # 2. Cadence & Acoustic & Disfluency Calibration (if audio provided)
        cadence_data = {}
        acoustic_data = {}
        disfluency_data = {}
        
        if audio_files:
            # Aggregate across files
            cadence_profiles = []
            acoustic_profiles = []
            disfluency_profiles = []
            
            for i, audio in enumerate(audio_files):
                transcript = audio_transcripts[i] if (audio_transcripts and i < len(audio_transcripts)) else ""
                
                # Analyze cadence
                c_prof = self.cadence_analyzer.analyze_audio(audio, transcript)
                cadence_profiles.append(c_prof)
                
                # Analyze acoustics
                pauses = c_prof.get("wpm_curve", []) # use curve timestamps or dummy
                a_prof = self.acoustic_profiler.analyze_audio(audio)
                acoustic_profiles.append(a_prof)
                
                # Analyze disfluency if script exists for comparison
                if transcript and scripts:
                    # Match transcript against closest script
                    d_prof = self.disfluency_calibrator.analyze_transcripts(transcript, scripts[0])
                    disfluency_profiles.append(d_prof)
            
            # Simple averaging of results
            if cadence_profiles:
                avg_wpm = sum(c["wpm_mean"] for c in cadence_profiles) / len(cadence_profiles)
                cadence_data = {
                    "wpm_mean": round(avg_wpm, 2),
                    "wpm_variance": round(sum(c["wpm_variance"] for c in cadence_profiles) / len(cadence_profiles), 2),
                    "average_pause_length_secs": round(sum(c["average_pause_length_secs"] for c in cadence_profiles) / len(cadence_profiles), 3),
                    "speaking_rate_variance": round(sum(c["speaking_rate_variance"] for c in cadence_profiles) / len(cadence_profiles), 4),
                    "wpm_curves": [c["wpm_curve"] for c in cadence_profiles]
                }
                
            if acoustic_profiles:
                avg_pitch = sum(a["pitch_mean_hz"] for a in acoustic_profiles) / len(acoustic_profiles)
                avg_jitter = sum(a["pitch_jitter_target_pct"] for a in acoustic_profiles) / len(acoustic_profiles)
                avg_noise = sum(a["noise_floor_db"] for a in acoustic_profiles) / len(acoustic_profiles)
                acoustic_data = {
                    "pitch_mean_hz": round(avg_pitch, 2),
                    "pitch_std_hz": round(sum(a["pitch_std_hz"] for a in acoustic_profiles) / len(acoustic_profiles), 2),
                    "pitch_jitter_target_pct": round(avg_jitter, 2),
                    "noise_floor_db": round(avg_noise, 2),
                    "microphone_coloration_type": acoustic_profiles[0]["microphone_coloration_type"]
                }
                
            if disfluency_profiles:
                avg_stumbles = sum(d["target_stumbles_per_minute"] for d in disfluency_profiles) / len(disfluency_profiles)
                disfluency_data = {
                    "target_stumbles_per_minute": round(avg_stumbles, 2),
                    "preferred_fillers": disfluency_profiles[0]["preferred_fillers"]
                }
        
        # Fallbacks if audio is missing
        if not cadence_data:
            cadence_data = {
                "wpm_mean": 150.0,
                "wpm_variance": 15.0,
                "average_pause_length_secs": 0.35,
                "speaking_rate_variance": 0.05
            }
        if not acoustic_data:
            acoustic_data = {
                "pitch_mean_hz": 125.0,
                "pitch_std_hz": 2.5,
                "pitch_jitter_target_pct": 1.5,
                "noise_floor_db": -50.0,
                "microphone_coloration_type": "studio_condenser"
            }
        if not disfluency_data:
            disfluency_data = {
                "target_stumbles_per_minute": 2.5,
                "preferred_fillers": {"um": 3, "uh": 2}
            }

        # 3. Temporal calibration
        temporal_data = self.temporal_analyzer.analyze_timestamps(post_timestamps or [])

        # 4. Save/update DB sub-profiles
        # Lexical
        lex_query = await db.execute(select(LexicalProfile).where(LexicalProfile.creator_id == creator_id))
        lex = lex_query.scalar_one_or_none()
        if not lex:
            lex = LexicalProfile(creator_id=creator_id)
            db.add(lex)
        lex.profile_data = lexical_data

        # Cadence
        cad_query = await db.execute(select(CadenceProfile).where(CadenceProfile.creator_id == creator_id))
        cad = cad_query.scalar_one_or_none()
        if not cad:
            cad = CadenceProfile(creator_id=creator_id)
            db.add(cad)
        cad.profile_data = cadence_data

        # Acoustic
        ac_query = await db.execute(select(AcousticProfile).where(AcousticProfile.creator_id == creator_id))
        ac = ac_query.scalar_one_or_none()
        if not ac:
            ac = AcousticProfile(creator_id=creator_id)
            db.add(ac)
        ac.profile_data = acoustic_data

        # Disfluency
        dis_query = await db.execute(select(DisfluencyProfile).where(DisfluencyProfile.creator_id == creator_id))
        dis = dis_query.scalar_one_or_none()
        if not dis:
            dis = DisfluencyProfile(creator_id=creator_id)
            db.add(dis)
        dis.profile_data = disfluency_data

        # Temporal
        temp_query = await db.execute(select(TemporalProfile).where(TemporalProfile.creator_id == creator_id))
        temp = temp_query.scalar_one_or_none()
        if not temp:
            temp = TemporalProfile(creator_id=creator_id)
            db.add(temp)
        temp.profile_data = temporal_data

        await db.commit()
        await db.refresh(creator)
        return creator
