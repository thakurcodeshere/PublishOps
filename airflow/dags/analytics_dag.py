"""
PublishOps — Analytics DAG
===========================
Hourly metrics collection with conditional weekly feedback loop trigger.
Lightweight — calls backend and returns quickly.
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
    dag_id="analytics",
    description="Hourly metrics collection with conditional feedback loop",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 2,
        "retry_delay": timedelta(seconds=30),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=10),
        "on_failure_callback": _on_failure,
    },
    tags=["analytics", "metrics"],
)
def analytics():
    """Collect platform metrics hourly and conditionally trigger feedback loop."""

    @task(task_id="collect_metrics")
    def collect_metrics() -> dict:
        """Call the backend to pull latest metrics from all connected platforms."""
        logger.info("Starting hourly metrics collection")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/analytics/collect",
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Metrics collected: %d posts updated across %d platforms",
                result.get("posts_updated", 0),
                result.get("platforms_queried", 0),
            )
            return result

    @task(task_id="check_feedback_loop_due")
    def check_feedback_loop_due(metrics_result: dict) -> bool:
        """Check if 7 days have passed since the last weight update."""
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(
                f"{BACKEND_URL}/api/v1/analytics/feedback-loop-status",
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            status = resp.json()
            is_due = status.get("is_due", False)
            days_since = status.get("days_since_last_update", 0)
            logger.info(
                "Feedback loop check: is_due=%s, days_since_last=%d",
                is_due,
                days_since,
            )
            return is_due

    @task(task_id="trigger_feedback_loop")
    def trigger_feedback_loop(is_due: bool) -> dict | None:
        """Trigger the feedback loop to recalculate algorithm weights if due."""
        if not is_due:
            logger.info("Feedback loop not due — skipping")
            return {"status": "skipped", "reason": "not_due"}

        logger.info("Triggering feedback loop weight recalculation")
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/analytics/feedback-loop",
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Feedback loop complete: %d weights updated",
                result.get("weights_updated", 0),
            )
            return result

    # Wire the pipeline
    metrics = collect_metrics()
    is_due = check_feedback_loop_due(metrics)
    trigger_feedback_loop(is_due)


analytics()
