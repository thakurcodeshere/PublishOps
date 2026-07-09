"""
PublishOps — Model Retraining & Evolution DAG
=============================================
Weekly self-learning cycle running every Monday at 4 AM UTC.
Triggers model evolution in the backend to keep generator models and gates aligned with audience success.
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
    dag_id="model_retrain_and_evolve",
    description="Weekly self-learning cycle — Retrain generator RAG, evolve Viral Gate XGBoost, register A/B experiments",
    schedule="0 4 * * 1",  # Monday 4 AM UTC
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=20),
    },
    tags=["self-learning", "weekly"],
)
def model_retrain_and_evolve():
    """Trigger the weekly model self-learning evolution stages."""

    @task(task_id="trigger_evolution")
    def trigger_evolution(dag_run=None) -> dict:
        """Call the backend evolve endpoint."""
        conf = dag_run.conf if dag_run else {}
        # Uses default UUID which the backend will resolve to the first available creator
        creator_id = conf.get("creator_id", "00000000-0000-0000-0000-000000000000")
        
        logger.info("Triggering model evolution for creator: %s", creator_id)
        
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/pipeline/evolve",
                json={"creator_id": creator_id},
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Evolution cycle completed successfully: %s", result.get("results"))
            return result

    trigger_evolution()


model_retrain_and_evolve()
