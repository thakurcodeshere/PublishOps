"""Timing jitter — randomise scheduled post times for human-like patterns."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TimingJitter:
    """Apply random timing offsets to scheduled posts for humanisation."""

    MAX_JITTER_MINUTES = 15
    MIN_INTER_PLATFORM_GAP_MINUTES = 20
    AVOID_MINUTES = {0, 30}  # Never post on the hour or half-hour

    def apply_jitter(
        self,
        scheduled_time: datetime,
        recent_posts: list[datetime] | None = None,
        is_weekend: bool | None = None,
    ) -> datetime:
        """
        Apply ±15min random offset to a scheduled time.

        Constraints:
        - Never land on :00 or :30
        - Minimum 20min gap from recent posts on other platforms
        - Weekend/weekday pattern variation
        """
        if is_weekend is None:
            is_weekend = scheduled_time.weekday() >= 5

        # Random jitter: ±15 minutes
        jitter = random.randint(-self.MAX_JITTER_MINUTES, self.MAX_JITTER_MINUTES)

        # Weekend shift: tend to post slightly later
        if is_weekend:
            jitter += random.randint(0, 10)

        jittered = scheduled_time + timedelta(minutes=jitter)

        # Avoid :00 and :30 minute marks
        while jittered.minute in self.AVOID_MINUTES:
            jittered += timedelta(minutes=random.choice([1, 2, -1, -2, 3]))

        # Ensure minimum gap from recent posts
        if recent_posts:
            for attempt in range(10):
                too_close = False
                for recent in recent_posts:
                    gap = abs((jittered - recent).total_seconds()) / 60
                    if gap < self.MIN_INTER_PLATFORM_GAP_MINUTES:
                        too_close = True
                        break
                if too_close:
                    jittered += timedelta(minutes=random.randint(5, 15))
                    while jittered.minute in self.AVOID_MINUTES:
                        jittered += timedelta(minutes=1)
                else:
                    break

        logger.info(
            "timing_jitter_applied",
            original=scheduled_time.isoformat(),
            jittered=jittered.isoformat(),
            offset_minutes=round((jittered - scheduled_time).total_seconds() / 60, 1),
        )
        return jittered

    def generate_schedule_pattern(
        self,
        base_times: list[datetime],
        platforms: list[str],
    ) -> list[tuple[str, datetime]]:
        """
        Generate a full posting schedule with jitter applied.

        Ensures inter-platform gaps and natural timing patterns.
        """
        schedule: list[tuple[str, datetime]] = []
        posted_times: list[datetime] = []

        for base_time, platform in zip(base_times, platforms, strict=False):
            jittered = self.apply_jitter(base_time, posted_times)
            schedule.append((platform, jittered))
            posted_times.append(jittered)

        return schedule
