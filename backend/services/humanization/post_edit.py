"""Post-edit — queue a delayed edit after upload for humanisation."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import redis.asyncio as redis

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

EDIT_TYPES = [
    "fix_typo",    # Fix a pre-planted "typo" in the post
    "add_emoji",   # Add an emoji to the caption
    "append_line", # Append a conversational line
]

EMOJI_POOL = ["🔥", "💡", "👀", "🤯", "📌", "✨", "🎯", "💪"]

APPEND_LINES = [
    "edit: wow this blew up, thanks for the love ❤️",
    "update: got a ton of DMs about this, doing a follow-up",
    "edit: just realized I should have mentioned...",
    "🔄 updated with a correction in the comments",
    "edit: adding this because someone asked a great question below 👇",
]


class PostEditor:
    """Queue and execute delayed post edits for humanisation signals."""

    EDIT_DELAY_MINUTES = 3

    def __init__(self) -> None:
        settings = get_settings()
        self._redis: redis.Redis | None = None
        self._redis_url = settings.REDIS_URL

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def queue_post_edit(
        self,
        post_id: str,
        platform: str,
        edit_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Queue a delayed post edit job.

        Edit triggers 3 minutes after upload confirmation.
        """
        if edit_type is None:
            edit_type = random.choice(EDIT_TYPES)

        edit_content = self._generate_edit_content(edit_type)
        execute_at = datetime.now(timezone.utc) + timedelta(minutes=self.EDIT_DELAY_MINUTES)

        job_data = {
            "job_id": str(uuid.uuid4()),
            "post_id": post_id,
            "platform": platform,
            "edit_type": edit_type,
            "edit_content": edit_content,
            "execute_at": execute_at.isoformat(),
            "status": "queued",
        }

        r = await self._get_redis()
        job_key = f"publishops:post_edit:{job_data['job_id']}"
        import json
        await r.setex(
            job_key,
            600,  # 10 minute TTL
            json.dumps(job_data),
        )

        # Add to sorted set for scheduled execution
        await r.zadd(
            "publishops:post_edits_scheduled",
            {job_data["job_id"]: execute_at.timestamp()},
        )

        logger.info(
            "post_edit_queued",
            job_id=job_data["job_id"],
            post_id=post_id,
            platform=platform,
            edit_type=edit_type,
            execute_at=execute_at.isoformat(),
        )
        return job_data

    def _generate_edit_content(self, edit_type: str) -> str:
        """Generate the content for the edit based on type."""
        if edit_type == "fix_typo":
            return "(typo fix applied)"
        elif edit_type == "add_emoji":
            return random.choice(EMOJI_POOL)
        elif edit_type == "append_line":
            return random.choice(APPEND_LINES)
        return ""

    async def get_pending_edits(self) -> list[dict[str, Any]]:
        """Get all edits that are ready to execute."""
        r = await self._get_redis()
        now = datetime.now(timezone.utc).timestamp()

        # Get job IDs whose execute_at has passed
        ready_ids: list[str] = await r.zrangebyscore(
            "publishops:post_edits_scheduled", "-inf", now
        )

        import json
        pending: list[dict[str, Any]] = []
        for job_id in ready_ids:
            data = await r.get(f"publishops:post_edit:{job_id}")
            if data:
                pending.append(json.loads(data))

        return pending

    async def mark_completed(self, job_id: str) -> None:
        """Mark a post edit as completed."""
        r = await self._get_redis()
        await r.zrem("publishops:post_edits_scheduled", job_id)
        await r.delete(f"publishops:post_edit:{job_id}")
        logger.info("post_edit_completed", job_id=job_id)
