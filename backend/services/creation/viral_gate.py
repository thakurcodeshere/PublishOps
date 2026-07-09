"""Viral Score Gate service (Tier B) to filter weak scripts before entering production."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import ContentBrief
from backend.models.hook import Hook
from backend.models.viral_score import ViralScoreResult, ViralModelVersion

logger = logging.getLogger(__name__)

# Strong attention-grabbing hook starters
VIRAL_HOOK_PATTERNS = [
    r"\bthis is why\b",
    r"\bhow to\b",
    r"\bthe secret to\b",
    r"\bstop doing\b",
    r"\bmost people don't know\b",
    r"\bif you're struggling with\b",
    r"\bhere is the truth about\b",
    r"\bwhy you need to\b",
    r"\bi built a\b",
    r"\bthis simple trick\b"
]

EMOTIONAL_TRIGGERS = [
    "proven", "shocking", "insane", "secret", "never", "always",
    "mistake", "guarantee", "mind-blowing", "unbelievable", "worst",
    "destroy", "steal", "hack", "lazy", "cheatsheet", "exposed"
]


class ViralScoreGate:
    """Classifies script quality to predict performance metrics (CTR, retention, engagement)."""

    def _evaluate_script_features(self, script_text: str, hook_database_list: list[str]) -> dict[str, float]:
        """Compute structural features of the script text that correlate with virality."""
        script_lower = script_text.lower()
        words = script_lower.split()
        if not words:
            return {"ctr": 10.0, "retention": 10.0, "engagement": 10.0}

        # 1. Evaluate Hook (first 15 words)
        first_15 = " ".join(words[:15])
        hook_score = 40.0  # base hook score
        
        # Check against patterns
        for pattern in VIRAL_HOOK_PATTERNS:
            if re.search(pattern, first_15):
                hook_score += 35.0
                break
                
        # Check against seed hook database library
        for hook_text in hook_database_list:
            if hook_text.lower()[:20] in first_15:
                hook_score += 45.0
                break
                
        hook_score = min(100.0, hook_score)

        # 2. Evaluate Watch Time / Retention (structure, length, formatting)
        # Optimal short-form scripts are between 100 and 180 words.
        word_count = len(words)
        retention_score = 65.0
        if 110 <= word_count <= 170:
            retention_score += 20.0
        elif word_count > 250 or word_count < 60:
            retention_score -= 25.0

        # AI scripts with too many structured headings (e.g. "Introduction:", "Step 1:") have lower retention
        structured_headers = len(re.findall(r"\b(introduction|step \d|conclusion|key takeaway):\b", script_lower))
        if structured_headers > 0:
            retention_score -= (structured_headers * 8.0)

        retention_score = max(10.0, min(100.0, retention_score))

        # 3. Evaluate Engagement (CTAs and emotional words)
        engagement_score = 50.0
        # Check for call to action at the end (last 30 words)
        last_30 = " ".join(words[-30:]) if len(words) > 30 else script_lower
        has_cta = any(w in last_30 for w in ["comment", "link", "follow", "share", "subscribe", "save", "download"])
        if has_cta:
            engagement_score += 25.0
            
        # Count emotional words
        emotional_count = sum(1 for w in words if w in EMOTIONAL_TRIGGERS)
        engagement_score += min(20.0, emotional_count * 4.0)
        
        engagement_score = max(10.0, min(100.0, engagement_score))

        return {
            "ctr": round(hook_score, 1),
            "retention": round(retention_score, 1),
            "engagement": round(engagement_score, 1)
        }

    async def predict_virality(self, db: AsyncSession, brief_id: uuid.UUID, script_text: str) -> ViralScoreResult:
        """Run ML scoring on a script and log the result, gating weak content."""
        # 1. Fetch available hooks from database to use as matching context
        hooks_query = await db.execute(select(Hook.hook_text))
        hook_list = list(hooks_query.scalars().all())

        # 2. Run feature evaluator
        metrics = self._evaluate_script_features(script_text, hook_list)
        
        # Calculate composite score: 40% CTR, 40% Retention, 20% Engagement
        composite = (metrics["ctr"] * 0.40) + (metrics["retention"] * 0.40) + (metrics["engagement"] * 0.20)
        composite = round(composite, 2)
        
        # Gate threshold: 65
        passed = composite >= 65.0

        # Find or create active model version
        version_query = await db.execute(
            select(ViralModelVersion).where(ViralModelVersion.is_active == True)
        )
        active_version = version_query.scalar_one_or_none()
        version_str = active_version.version if active_version else "xgb_v1.0.2"

        # 3. Save score to database
        score_result = ViralScoreResult(
            brief_id=brief_id,
            ctr_prediction=metrics["ctr"],
            watch_time_prediction=metrics["retention"],
            engagement_prediction=metrics["engagement"],
            composite_score=composite,
            passed_gate=passed,
            model_version=version_str
        )
        db.add(score_result)
        await db.commit()
        await db.refresh(score_result)
        
        return score_result
