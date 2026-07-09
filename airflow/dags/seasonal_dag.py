"""
PublishOps — Seasonal Calendar Planning DAG
===========================================
Daily recurring task running at 1 AM UTC.
Queries upcoming cultural/seasonal events, plans campaigns 3-4 weeks ahead of peak search volume,
and generates content briefs.
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

HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)


@dag(
    dag_id="seasonal_planning",
    description="Daily check for upcoming seasonal calendar events and planning content briefs",
    schedule="0 1 * * *",  # Daily at 1 AM UTC
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 2,
        "retry_delay": timedelta(minutes=3),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["growth", "seasonal", "daily"],
)
def seasonal_planning():
    """Trigger daily seasonal content discovery and brief creation."""

    @task(task_id="check_upcoming_events")
    def check_upcoming_events() -> dict:
        """Call the backend seasonal endpoint to discover and create briefs."""
        logger.info("Scanning seasonal calendar for events in lookahead window")
        
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/pipeline/seasonal",
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Checked %d events. Generated %d content briefs.", result.get("events_checked", 0), len(result.get("briefs_created", [])))
            return result

    check_upcoming_events()


seasonal_planning()
