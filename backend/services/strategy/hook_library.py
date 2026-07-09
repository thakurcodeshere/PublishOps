"""Hook library — load, select, and update performance of content hooks."""

from __future__ import annotations

import random
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.hook import Hook
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class HookLibrary:
    """Manage a library of reusable hooks with performance-weighted selection."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._hooks: list[Hook] = []
        self._loaded = False

    async def load_hooks(self) -> list[Hook]:
        """Load all hooks from the database."""
        result = await self._session.execute(select(Hook))
        self._hooks = list(result.scalars().all())
        self._loaded = True
        logger.info("hooks_loaded", count=len(self._hooks))
        return self._hooks

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self.load_hooks()

    def _calculate_selection_weight(
        self,
        hook: Hook,
        platform: str,
        emotion: str,
    ) -> float:
        """
        Calculate selection weight for a hook.

        Weight = performance_score × platform_affinity × emotion_match
        """
        # Performance score (normalised 0-1, default 0.5 for new hooks)
        perf = max(hook.avg_performance, 0.1) if hook.avg_performance > 0 else 0.5

        # Platform affinity
        affinity = 0.5  # Default
        if hook.platform_affinity and isinstance(hook.platform_affinity, dict):
            affinity = hook.platform_affinity.get(platform.lower(), 0.5)

        # Emotion match (binary boost)
        emotion_match = 1.5 if hook.target_emotion.lower() == emotion.lower() else 0.8

        # Usage penalty (slightly favour less-used hooks for variety)
        usage_penalty = 1.0 / (1.0 + hook.usage_count * 0.01)

        weight = perf * affinity * emotion_match * usage_penalty
        return max(weight, 0.01)  # Ensure non-zero

    async def select_hook(
        self,
        topic_title: str,
        platform: str,
        emotion: str,
    ) -> Hook | None:
        """
        Select a hook using weighted random selection.

        Weight = performance_score × platform_affinity × emotion_match
        """
        await self._ensure_loaded()

        if not self._hooks:
            logger.warning("no_hooks_available")
            return None

        # Filter to relevant hooks (matching emotion or high performers)
        relevant = [
            h for h in self._hooks
            if h.target_emotion.lower() == emotion.lower()
            or h.avg_performance > 0.7
        ]

        if not relevant:
            relevant = self._hooks  # Fall back to all hooks

        # Calculate weights
        weights = [
            self._calculate_selection_weight(h, platform, emotion)
            for h in relevant
        ]

        # Weighted random selection
        selected = random.choices(relevant, weights=weights, k=1)[0]

        # Increment usage count
        selected.usage_count += 1
        await self._session.execute(
            update(Hook)
            .where(Hook.id == selected.id)
            .values(usage_count=selected.usage_count)
        )

        logger.info(
            "hook_selected",
            hook_id=str(selected.id),
            hook_type=selected.hook_type,
            platform=platform,
            emotion=emotion,
        )
        return selected

    async def update_hook_score(
        self,
        hook_id: uuid.UUID,
        performance: float,
    ) -> None:
        """
        Update a hook's average performance score.

        Uses exponential moving average: new_avg = 0.3 * performance + 0.7 * old_avg
        """
        result = await self._session.execute(
            select(Hook).where(Hook.id == hook_id)
        )
        hook = result.scalar_one_or_none()
        if not hook:
            logger.warning("hook_not_found_for_update", hook_id=str(hook_id))
            return

        alpha = 0.3  # Learning rate
        new_avg = alpha * performance + (1 - alpha) * hook.avg_performance

        await self._session.execute(
            update(Hook)
            .where(Hook.id == hook_id)
            .values(avg_performance=round(new_avg, 4))
        )

        logger.info(
            "hook_score_updated",
            hook_id=str(hook_id),
            old_score=hook.avg_performance,
            new_score=round(new_avg, 4),
            performance_input=performance,
        )

    async def add_hook(
        self,
        text: str,
        hook_type: str,
        target_emotion: str,
        platform_affinity: dict[str, float] | None = None,
    ) -> Hook:
        """Add a new hook to the library."""
        hook = Hook(
            text=text,
            hook_type=hook_type,
            target_emotion=target_emotion,
            platform_affinity=platform_affinity or {},
            usage_count=0,
            avg_performance=0.5,  # Start neutral
        )
        self._session.add(hook)
        await self._session.flush()
        self._hooks.append(hook)
        logger.info("hook_added", hook_id=str(hook.id), hook_type=hook_type)
        return hook
