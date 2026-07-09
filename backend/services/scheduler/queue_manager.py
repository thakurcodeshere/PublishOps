"""Queue manager — Redis-backed job queue for scheduled uploads."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

QUEUE_PREFIX = "publishops:upload_queue"
PRIORITY_SCORES = {"urgent": 0, "normal": 100, "low": 200}


class QueueManager:
    """Redis-backed priority queue for scheduled upload jobs."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def create_upload_job(
        self,
        variant_id: uuid.UUID,
        platform: str,
        scheduled_time: datetime,
        s3_key: str = "",
        priority: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an upload job in the priority queue.

        Priority: urgent (0) > normal (100) > low (200)
        Score = priority_offset + unix_timestamp (lower runs first)
        """
        r = await self._get_redis()
        job_id = str(uuid.uuid4())

        job_data = {
            "job_id": job_id,
            "variant_id": str(variant_id),
            "platform": platform,
            "scheduled_time": scheduled_time.isoformat(),
            "s3_key": s3_key,
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Store job data
        await r.set(f"{QUEUE_PREFIX}:job:{job_id}", json.dumps(job_data), ex=86400 * 7)

        # Add to priority sorted set
        priority_offset = PRIORITY_SCORES.get(priority, 100)
        score = priority_offset + scheduled_time.timestamp()
        await r.zadd(f"{QUEUE_PREFIX}:scheduled", {job_id: score})

        # Track per-platform
        await r.sadd(f"{QUEUE_PREFIX}:platform:{platform}", job_id)

        logger.info(
            "upload_job_created",
            job_id=job_id,
            platform=platform,
            priority=priority,
            scheduled_time=scheduled_time.isoformat(),
        )
        return job_id

    async def get_due_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get jobs that are due for execution (scheduled_time has passed)."""
        r = await self._get_redis()
        now = datetime.now(timezone.utc).timestamp() + 200  # Include normal priority offset

        job_ids = await r.zrangebyscore(
            f"{QUEUE_PREFIX}:scheduled", "-inf", now, start=0, num=limit
        )

        jobs: list[dict[str, Any]] = []
        for job_id in job_ids:
            data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
            if data:
                job = json.loads(data)
                scheduled = datetime.fromisoformat(job["scheduled_time"])
                if scheduled <= datetime.now(timezone.utc):
                    jobs.append(job)

        return jobs

    async def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status."""
        r = await self._get_redis()
        total = await r.zcard(f"{QUEUE_PREFIX}:scheduled")

        now = datetime.now(timezone.utc).timestamp() + 200
        due = await r.zcount(f"{QUEUE_PREFIX}:scheduled", "-inf", now)

        platforms: dict[str, int] = {}
        for platform in ["youtube", "tiktok", "instagram", "twitter", "linkedin"]:
            count = await r.scard(f"{QUEUE_PREFIX}:platform:{platform}")
            if count > 0:
                platforms[platform] = count

        return {
            "total_jobs": total,
            "due_now": due,
            "pending": total - due,
            "by_platform": platforms,
        }

    async def mark_completed(self, job_id: str) -> None:
        """Mark a job as completed and remove from queue."""
        r = await self._get_redis()
        await r.zrem(f"{QUEUE_PREFIX}:scheduled", job_id)

        data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
        if data:
            job = json.loads(data)
            job["status"] = "completed"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            await r.set(f"{QUEUE_PREFIX}:job:{job_id}", json.dumps(job), ex=86400 * 7)
            await r.srem(f"{QUEUE_PREFIX}:platform:{job['platform']}", job_id)

        logger.info("upload_job_completed", job_id=job_id)

    async def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""
        r = await self._get_redis()
        data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
        if data:
            job = json.loads(data)
            job["status"] = "failed"
            job["error"] = error
            job["failed_at"] = datetime.now(timezone.utc).isoformat()
            await r.set(f"{QUEUE_PREFIX}:job:{job_id}", json.dumps(job), ex=86400 * 7)

        logger.error("upload_job_failed", job_id=job_id, error=error)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        r = await self._get_redis()
        removed = await r.zrem(f"{QUEUE_PREFIX}:scheduled", job_id)
        if removed:
            data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
            if data:
                job = json.loads(data)
                job["status"] = "cancelled"
                await r.set(f"{QUEUE_PREFIX}:job:{job_id}", json.dumps(job), ex=86400)
                await r.srem(f"{QUEUE_PREFIX}:platform:{job['platform']}", job_id)
            logger.info("upload_job_cancelled", job_id=job_id)
            return True
        return False

    async def get_upcoming(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get upcoming scheduled jobs sorted by time."""
        r = await self._get_redis()
        job_ids = await r.zrange(f"{QUEUE_PREFIX}:scheduled", 0, limit - 1)

        jobs: list[dict[str, Any]] = []
        for job_id in job_ids:
            data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
            if data:
                jobs.append(json.loads(data))

        return jobs

    async def ensure_content_buffer(self, hours: int = 24) -> dict[str, int]:
        """Check how many hours of content buffer each platform has."""
        r = await self._get_redis()
        buffer: dict[str, int] = {}
        now = datetime.now(timezone.utc)
        buffer_end = now + __import__("datetime").timedelta(hours=hours)

        for platform in ["youtube", "tiktok", "instagram", "twitter", "linkedin"]:
            job_ids = await r.smembers(f"{QUEUE_PREFIX}:platform:{platform}")
            count = 0
            for job_id in job_ids:
                data = await r.get(f"{QUEUE_PREFIX}:job:{job_id}")
                if data:
                    job = json.loads(data)
                    scheduled = datetime.fromisoformat(job["scheduled_time"])
                    if now <= scheduled <= buffer_end:
                        count += 1
            buffer[platform] = count

        return buffer
