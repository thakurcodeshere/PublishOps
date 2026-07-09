"""Calibration API routes (Tier C) for creator fingerprint and Voice Bible management."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.creator_profile import CreatorProfile, OpinionEntry
from backend.services.fingerprint.engine import CreatorFingerprintEngine
from backend.services.fingerprint.opinion_store import OpinionStore

router = APIRouter()
fingerprint_engine = CreatorFingerprintEngine()
opinion_store = OpinionStore()

# ── Pydantic Request/Response Schemas ─────────────────────────────────

class CreatorCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CreatorResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    lexical_profile: dict[str, Any] | None = None
    cadence_profile: dict[str, Any] | None = None
    acoustic_profile: dict[str, Any] | None = None
    disfluency_profile: dict[str, Any] | None = None
    temporal_profile: dict[str, Any] | None = None


class ScriptsUploadRequest(BaseModel):
    creator_id: uuid.UUID
    scripts: list[str]


class OpinionCreateRequest(BaseModel):
    creator_id: uuid.UUID
    topic: str
    stance: str
    allowed_terms: list[str] = []
    forbidden_terms: list[str] = []


class OpinionResponse(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    topic: str
    stance: str
    allowed_terms: list[str]
    forbidden_terms: list[str]


class AnalyzeTriggerRequest(BaseModel):
    creator_id: uuid.UUID
    scripts: list[str] = []
    audio_transcripts: list[str] = []

# ── API Routes ────────────────────────────────────────────────────────

@router.post("/creator", response_model=CreatorResponse)
async def create_creator(
    body: CreatorCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Create a new creator profile."""
    creator = await fingerprint_engine.get_or_create_creator(db, body.name, body.description)
    return {
        "id": creator.id,
        "name": creator.name,
        "description": creator.description,
        "lexical_profile": None,
        "cadence_profile": None,
        "acoustic_profile": None,
        "disfluency_profile": None,
        "temporal_profile": None,
    }


@router.get("/profile/{creator_id}", response_model=CreatorResponse)
async def get_creator_profile(
    creator_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Fetch the fully calibrated profile of a creator."""
    creator = await fingerprint_engine.get_profile(db, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    return {
        "id": creator.id,
        "name": creator.name,
        "description": creator.description,
        "lexical_profile": creator.lexical.profile_data if creator.lexical else None,
        "cadence_profile": creator.cadence.profile_data if creator.cadence else None,
        "acoustic_profile": creator.acoustic.profile_data if creator.acoustic else None,
        "disfluency_profile": creator.disfluency.profile_data if creator.disfluency else None,
        "temporal_profile": creator.temporal.profile_data if creator.temporal else None,
    }


@router.post("/upload-audio", response_model=dict)
async def upload_calibration_audio(
    creator_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Upload a reference audio file for cadence, acoustic, and disfluency profiling."""
    creator = await fingerprint_engine.get_profile(db, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    content = await file.read()
    
    # Save the file locally to data/calibration/audio/
    upload_dir = os.path.join("data", "calibration", "audio")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{creator_id}_{file.filename}")
    
    with open(file_path, "wb") as f:
        f.write(content)

    # Trigger a partial calibration run with the uploaded audio
    await fingerprint_engine.calibrate_creator(
        db=db,
        creator_id=creator_id,
        scripts=[],  # keep existing
        audio_files=[content],
        audio_transcripts=[""]  # empty or generated if STT exists
    )

    return {
        "filename": file.filename,
        "saved_path": file_path,
        "creator_id": str(creator_id),
        "status": "calibrated"
    }


@router.post("/upload-scripts", response_model=dict)
async def upload_calibration_scripts(
    body: ScriptsUploadRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Upload a list of historical scripts/posts for lexical mapping."""
    creator = await fingerprint_engine.get_profile(db, body.creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    await fingerprint_engine.calibrate_creator(
        db=db,
        creator_id=body.creator_id,
        scripts=body.scripts
    )

    return {
        "creator_id": str(body.creator_id),
        "scripts_processed": len(body.scripts),
        "status": "calibrated"
    }


@router.post("/analyze", response_model=CreatorResponse)
async def trigger_full_analysis(
    body: AnalyzeTriggerRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Trigger full profiling engine calibration on demand."""
    creator = await fingerprint_engine.get_profile(db, body.creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    updated = await fingerprint_engine.calibrate_creator(
        db=db,
        creator_id=body.creator_id,
        scripts=body.scripts,
        audio_transcripts=body.audio_transcripts
    )

    return await get_creator_profile(updated.id, db)


# ── Voice Bible / Opinion CRUD ────────────────────────────────────────

@router.post("/voice-bible", response_model=OpinionResponse)
async def create_opinion(
    body: OpinionCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Add a new voice stance / constraint to the Voice Bible."""
    entry = await opinion_store.add_opinion(
        db=db,
        creator_id=body.creator_id,
        topic=body.topic,
        stance=body.stance,
        allowed_terms=body.allowed_terms,
        forbidden_terms=body.forbidden_terms
    )
    return {
        "id": entry.id,
        "creator_id": entry.creator_id,
        "topic": entry.topic,
        "stance": entry.stance,
        "allowed_terms": entry.allowed_terms.get("terms", []),
        "forbidden_terms": entry.forbidden_terms.get("terms", []),
    }


@router.get("/voice-bible/{creator_id}", response_model=list[OpinionResponse])
async def get_voice_bible(
    creator_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Retrieve the entire Voice Bible for a creator."""
    entries = await opinion_store.get_opinions(db, creator_id)
    return [
        {
            "id": e.id,
            "creator_id": e.creator_id,
            "topic": e.topic,
            "stance": e.stance,
            "allowed_terms": e.allowed_terms.get("terms", []),
            "forbidden_terms": e.forbidden_terms.get("terms", []),
        }
        for e in entries
    ]


@router.delete("/voice-bible/{opinion_id}", response_model=dict)
async def delete_opinion(
    opinion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Remove a voice constraint from the Voice Bible."""
    await opinion_store.delete_opinion(db, opinion_id)
    return {"status": "deleted", "id": str(opinion_id)}
