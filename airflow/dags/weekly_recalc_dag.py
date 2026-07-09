"""
PublishOps — Weekly Recalculation DAG
=======================================
Runs every Monday at 3 AM UTC to recalculate optimal posting windows
based on the latest audience analytics data.
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

HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)


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
    dag_id="weekly_recalc",
    description="Weekly posting window recalculation using audience analytics",
    schedule="0 3 * * 1",  # Monday 3 AM UTC
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=15),
        "execution_timeout": timedelta(minutes=30),
        "on_failure_callback": _on_failure,
    },
    tags=["scheduler", "weekly"],
)
def weekly_recalc():
    """Pull audience analytics and recalculate optimal posting windows per platform."""

    @task(task_id="pull_audience_analytics")
    def pull_audience_analytics() -> dict:
        """Fetch the latest 7-day audience activity data from all platforms."""
        logger.info("Pulling audience analytics for the past 7 days")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/analytics/audience-activity",
                json={"lookback_days": 7},
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Audience analytics received for %d platforms",
                result.get("platforms_count", 0),
            )
            return result

    @task(task_id="recalculate_windows")
    def recalculate_windows(audience_data: dict) -> dict:
        """Recalculate optimal posting windows based on audience activity patterns."""
        logger.info("Recalculating posting windows")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/scheduler/recalculate-windows",
                json=audience_data,
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Recalculated windows for %d platforms, %d time slots updated",
                result.get("platforms_updated", 0),
                result.get("slots_updated", 0),
            )
            return result

    @task(task_id="notify_completion")
    def notify_completion(recalc_result: dict) -> dict:
        """Send a summary notification about the recalculated windows."""
        logger.info("Sending weekly recalculation summary")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/alerts/weekly-summary",
                json={
                    "type": "posting_windows_recalculated",
                    "result": recalc_result,
                },
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            return resp.json()

    # Wire the pipeline
    audience = pull_audience_analytics()
    recalc = recalculate_windows(audience)
    notify_completion(recalc)


weekly_recalc()
