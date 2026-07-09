"""Window calculator — optimal posting windows per platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Default peak engagement windows (UTC offsets for US audience)
_DEFAULT_WINDOWS: dict[str, list[dict[str, Any]]] = {
    "youtube": [
        {"day": "weekday", "start_hour": 14, "end_hour": 17, "weight": 1.0},
        {"day": "weekday", "start_hour": 19, "end_hour": 21, "weight": 0.8},
        {"day": "weekend", "start_hour": 10, "end_hour": 13, "weight": 0.9},
    ],
    "tiktok": [
        {"day": "weekday", "start_hour": 11, "end_hour": 13, "weight": 0.8},
        {"day": "weekday", "start_hour": 19, "end_hour": 22, "weight": 1.0},
        {"day": "weekend", "start_hour": 12, "end_hour": 15, "weight": 0.9},
    ],
    "instagram": [
        {"day": "weekday", "start_hour": 11, "end_hour": 14, "weight": 0.9},
        {"day": "weekday", "start_hour": 19, "end_hour": 21, "weight": 1.0},
        {"day": "weekend", "start_hour": 10, "end_hour": 14, "weight": 0.85},
    ],
    "twitter": [
        {"day": "weekday", "start_hour": 8, "end_hour": 10, "weight": 0.9},
        {"day": "weekday", "start_hour": 12, "end_hour": 14, "weight": 1.0},
        {"day": "weekday", "start_hour": 17, "end_hour": 19, "weight": 0.8},
    ],
    "linkedin": [
        {"day": "weekday", "start_hour": 7, "end_hour": 9, "weight": 1.0},
        {"day": "weekday", "start_hour": 12, "end_hour": 13, "weight": 0.8},
        {"day": "weekday", "start_hour": 17, "end_hour": 18, "weight": 0.7},
    ],
    "pinterest": [
        {"day": "weekday", "start_hour": 14, "end_hour": 16, "weight": 1.0},
        {"day": "weekday", "start_hour": 20, "end_hour": 22, "weight": 0.8},
        {"day": "weekend", "start_hour": 12, "end_hour": 17, "weight": 0.9},
    ],
}

MIN_SELF_POST_GAP_HOURS = 4


@dataclass
class TimeWindow:
    """An optimal posting time window."""

    platform: str
    start: datetime
    end: datetime
    weight: float
    reason: str


class WindowCalculator:
    """Calculate optimal posting windows based on audience activity patterns."""

    def __init__(self) -> None:
        self._windows = _DEFAULT_WINDOWS

    def calculate_optimal_windows(
        self,
        platform: str,
        audience_data: dict[str, Any] | None = None,
        existing_posts: list[datetime] | None = None,
        days_ahead: int = 7,
    ) -> list[TimeWindow]:
        """
        Calculate optimal posting windows for a platform.

        Considers:
        - Default peak engagement windows
        - Audience activity data (if available)
        - Existing scheduled posts (4h minimum gap)
        - Timezone distribution
        """
        platform_lower = platform.lower()
        windows_config = self._windows.get(platform_lower, self._windows["youtube"])
        existing = existing_posts or []
        now = datetime.now(timezone.utc)

        results: list[TimeWindow] = []

        for day_offset in range(days_ahead):
            target_date = now + timedelta(days=day_offset)
            is_weekend = target_date.weekday() >= 5
            day_type = "weekend" if is_weekend else "weekday"

            for window in windows_config:
                if window["day"] != day_type:
                    continue

                start = target_date.replace(
                    hour=window["start_hour"], minute=0, second=0, microsecond=0
                )
                end = target_date.replace(
                    hour=window["end_hour"], minute=0, second=0, microsecond=0
                )

                if start < now:
                    continue

                # Check 4h gap from existing posts
                too_close = False
                for ep in existing:
                    gap_hours = abs((start - ep).total_seconds()) / 3600
                    if gap_hours < MIN_SELF_POST_GAP_HOURS:
                        too_close = True
                        break

                if too_close:
                    continue

                weight = window["weight"]

                # Adjust weight based on audience data
                if audience_data:
                    active_hours = audience_data.get("active_hours", {})
                    hour_activity = active_hours.get(str(window["start_hour"]), 0.5)
                    weight = (weight + hour_activity) / 2

                    tz_distribution = audience_data.get("timezone_weights", {})
                    if tz_distribution:
                        tz_boost = sum(tz_distribution.values()) / max(len(tz_distribution), 1)
                        weight *= (0.5 + tz_boost * 0.5)

                results.append(
                    TimeWindow(
                        platform=platform_lower,
                        start=start,
                        end=end,
                        weight=round(weight, 3),
                        reason=f"Peak {day_type} window {window['start_hour']}:00-{window['end_hour']}:00 UTC",
                    )
                )

        results.sort(key=lambda w: w.weight, reverse=True)

        logger.info(
            "windows_calculated",
            platform=platform,
            total_windows=len(results),
            days_ahead=days_ahead,
        )
        return results

    async def get_next_optimal_time(
        self,
        platform: str,
        existing_posts: list[datetime] | None = None,
        db: Any | None = None,
        creator_id: Any | None = None,
    ) -> datetime | None:
        """Get the single next best posting time, applying creator temporal jitter."""
        windows = self.calculate_optimal_windows(
            platform=platform,
            existing_posts=existing_posts,
            days_ahead=3,
        )
        if windows:
            best = windows[0]
            base_time = best.start
            
            # Apply creator jitter if temporal profile is available
            if db and creator_id:
                try:
                    from backend.models.creator_profile import CreatorProfile
                    from backend.services.fingerprint.temporal_analyzer import TemporalAnalyzer
                    from sqlalchemy import select
                    
                    creator_res = await db.execute(
                        select(CreatorProfile).where(CreatorProfile.id == creator_id)
                    )
                    creator = creator_res.scalar_one_or_none()
                    
                    if creator and creator.temporal:
                        analyzer = TemporalAnalyzer()
                        jittered = analyzer.calculate_jitter(base_time, creator.temporal.profile_data)
                        logger.info("scheduled_time_jitter_applied", platform=platform, original=base_time.isoformat(), jittered=jittered.isoformat())
                        return jittered
                except Exception as e:
                    logger.warning(f"Failed to apply temporal jitter, using standard random minute: {e}")

            # Standard random minute fallback (averaging 10 minutes jitter)
            import random
            offset = random.randint(3, 27)
            # Adjust to avoid hitting round 15-minute marks
            if offset in [0, 15, 30, 45, 60]:
                offset += 2
            return base_time + timedelta(minutes=offset)
        return None
