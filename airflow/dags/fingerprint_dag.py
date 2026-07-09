"""
PublishOps — Creator Fingerprint Calibration DAG
================================================
Runs one-shot or manually triggered to calibrate the Creator Fingerprint Engine
across lexical, cadence, acoustic, disfluency, and temporal profiles.
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
    dag_id="creator_calibration",
    description="One-shot Creator Fingerprint profiling and calibration run",
    schedule=None,  # Manual trigger
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["fingerprint", "calibration"],
)
def creator_calibration():
    """Trigger full Creator Fingerprint calibration in the backend."""

    @task(task_id="calibrate_creator_profile")
    def calibrate_creator_profile(dag_run=None) -> dict:
        """Call the backend calibration analyze endpoint."""
        # Retrieve creator_id from conf if passed, otherwise default to a test UUID or query it in DB
        conf = dag_run.conf if dag_run else {}
        creator_id = conf.get("creator_id", "00000000-0000-0000-0000-000000000000")
        
        logger.info("Starting profiling analysis calibration for creator: %s", creator_id)
        
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/calibration/analyze",
                json={
                    "creator_id": creator_id,
                    "scripts": conf.get("scripts", []),
                    "audio_transcripts": conf.get("audio_transcripts", [])
                },
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Calibrated profile: %s", result.get("name"))
            return result

    calibrate_creator_profile()


creator_calibration()
