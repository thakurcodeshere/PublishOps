"""
PublishOps — Repost DAG
========================
Daily check at 2 AM UTC for top-performing content eligible for reposting.
Finds 30-day-old top performers and queues repost jobs.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import httpx
import pendulum
from airflow.decorators import dag, task
from airflow.models import Variable

logger = logging.getLogger(__name__)

BACKEND_URL = Variable.get("backend_url", default_var="http://backend:8000")
BACKEND_API_KEY = Variable.get("backend_api_key", default_var="internal-api-key-replace-me")

DEFAULT_HEADERS = {
    "Authorization": f"Bearer {BACKEND_API_KEY}",
    "Content-Type": "application/json",
}

HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)


def _on_failure(context):
    """Alert on task failure via backend webhook."""
    task_instance = context["task_instance"]
    dag_id = context["dag"].dag_id
    error_msg = str(context.get("exception", "Unknown error"))
    logger.error("Task %s in DAG %s failed: %s", task_instance.task_id, dag_id, error_msg)
    try:
        httpx.post(
            f"{BACKEND_URL}/api/v1/alerts/pipeline-failure",
            json={
                "dag_id": dag_id,
                "task_id": task_instance.task_id,
                "execution_date": str(context["execution_date"]),
                "error": error_msg,
            },
            headers=DEFAULT_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
    except Exception:
        logger.exception("Failed to send pipeline failure alert")


@dag(
    dag_id="repost",
    description="Daily repost check — find and queue 30-day-old top performers",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=15),
        "on_failure_callback": _on_failure,
    },
    tags=["repost", "recycling"],
)
def repost():
    """Identify top-performing content from 30+ days ago and queue for reposting."""

    @task(task_id="check_repost_candidates")
    def check_repost_candidates() -> dict:
        """Call the backend to find content eligible for reposting.

        Criteria:
        - Published >= 30 days ago
        - Performance in top 20% by engagement score
        - Not already reposted within the last 60 days
        - Content type eligible for repost (evergreen topics)
        """
        logger.info("Checking for repost-eligible content")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/analytics/check-reposts",
                json={
                    "min_age_days": 30,
                    "top_percentile": 0.20,
                    "repost_cooldown_days": 60,
                },
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Found %d repost candidates out of %d evaluated",
                result.get("candidates_count", 0),
                result.get("evaluated_count", 0),
            )
            return result

    @task(task_id="queue_reposts")
    def queue_reposts(candidates: dict) -> dict:
        """Queue approved repost candidates for content regeneration and scheduling."""
        candidate_list = candidates.get("candidates", [])
        if not candidate_list:
            logger.info("No repost candidates found — nothing to queue")
            return {"queued": 0}

        logger.info("Queuing %d repost jobs", len(candidate_list))
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/pipeline/queue-reposts",
                json={"candidates": candidate_list},
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Queued %d repost jobs", result.get("queued", 0))
            return result

    # Wire tasks
    candidates = check_repost_candidates()
    queue_reposts(candidates)


repost()
