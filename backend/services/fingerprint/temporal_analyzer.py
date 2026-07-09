"""Temporal analyzer service (Tier C) for profiling publishing patterns and calculating scheduling jitter."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any


class TemporalAnalyzer:
    """Analyzes posting times and generates natural human publishing schedules with realistic jitter."""

    def analyze_timestamps(self, publish_datetimes: list[datetime]) -> dict[str, Any]:
        """Analyze historical posting datetimes to extract scheduling preferences.
        
        Args:
            publish_datetimes: List of past publishing datetimes.
            
        Returns:
            A temporal profile dictionary.
        """
        if not publish_datetimes:
            return {
                "preferred_days": [0, 1, 2, 3, 4],  # Mon-Fri
                "preferred_hours": [9, 12, 15, 18],
                "avg_jitter_minutes": 10.0,
                "hour_distribution": {},
                "day_distribution": {}
            }

        # Analyze hour and day distribution
        hour_counts: dict[int, int] = {}
        day_counts: dict[int, int] = {}
        
        for dt in publish_datetimes:
            hour = dt.hour
            day = dt.weekday()  # Monday is 0, Sunday is 6
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            day_counts[day] = day_counts.get(day, 0) + 1

        # Find hours with > 15% of posts
        total_posts = len(publish_datetimes)
        preferred_hours = [h for h, c in hour_counts.items() if (c / total_posts) >= 0.1]
        preferred_days = [d for d, c in day_counts.items() if (c / total_posts) >= 0.1]

        # Calculate standard deviation of minutes offset from round half-hours
        offsets = []
        for dt in publish_datetimes:
            # Distance to nearest 30-min boundary
            min_val = dt.minute + dt.second / 60.0
            dist_to_00 = min_val
            dist_to_30 = abs(min_val - 30.0)
            dist_to_60 = 60.0 - min_val
            offset = min(dist_to_00, dist_to_30, dist_to_60)
            offsets.append(offset)

        avg_jitter = sum(offsets) / len(offsets) if offsets else 8.5
        avg_jitter = max(3.0, min(18.0, avg_jitter))  # Bound between 3 and 18 mins

        # Sort distributions for return
        hour_dist = {f"{h:02d}:00": round((c / total_posts) * 100, 1) for h, c in sorted(hour_counts.items())}
        day_dist = {str(d): round((c / total_posts) * 100, 1) for d, c in sorted(day_counts.items())}

        return {
            "preferred_days": preferred_days or [0, 1, 2, 3, 4],
            "preferred_hours": preferred_hours or [9, 12, 15, 18],
            "avg_jitter_minutes": round(avg_jitter, 1),
            "hour_distribution": hour_dist,
            "day_distribution": day_dist
        }

    def calculate_jitter(self, target_time: datetime, profile: dict[str, Any]) -> datetime:
        """Add randomized jitter to a scheduled publication time to simulate human behavior.
        
        Guarantees that the resulting time is never exactly on the hour, half-hour, or 15-minute marks.
        """
        avg_jitter = profile.get("avg_jitter_minutes", 10.0)
        
        # Jitter can be negative or positive
        jitter_min = int(avg_jitter)
        if jitter_min < 3:
            jitter_min = 3

        # Generate a random offset in seconds
        offset_seconds = random.randint(-jitter_min * 60, jitter_min * 60)
        jittered_time = target_time + timedelta(seconds=offset_seconds)
        
        # Verify and adjust if it hits round markers
        attempts = 0
        while attempts < 10:
            minute = jittered_time.minute
            second = jittered_time.second
            
            # Check if within 45 seconds of a 15-minute interval (:00, :15, :30, :45)
            is_near_round_number = False
            for round_mark in [0, 15, 30, 45, 60]:
                diff_sec = abs((minute * 60 + second) - (round_mark * 60))
                if diff_sec < 45:
                    is_near_round_number = True
                    break
            
            if not is_near_round_number:
                break
                
            # If round, add/subtract random seconds to break the alignment
            adjust_sec = random.choice([-150, -90, -75, 75, 90, 150])
            jittered_time += timedelta(seconds=adjust_sec)
            attempts += 1
            
        return jittered_time
