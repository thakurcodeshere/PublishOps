"""
PublishOps — Intelligence DAG
==============================
Trend scraping every 2 hours with 10 parallel scrapers.
Each scraper runs independently; failures are graceful (pipeline continues).
A downstream scorer runs after all scrapers complete.
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

SCRAPERS = [
    "google_trends",
    "twitter_trending",
    "tiktok_discover",
    "youtube_trending",
    "reddit_popular",
    "instagram_explore",
    "linkedin_trending",
    "news_api",
    "hackernews_top",
    "pinterest_trends",
]


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
    dag_id="intelligence",
    description="Trend scraping across 10 sources every 2 hours",
    schedule="0 */2 * * *",
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
    tags=["intelligence", "scraping"],
)
def intelligence():
    """Scrape trends from 10 sources in parallel, then score results."""

    @task(task_id="scrape_source", trigger_rule="all_done")
    def scrape_source(scraper_name: str) -> dict:
        """Trigger a single scraper via the backend API.

        Uses trigger_rule='all_done' so downstream scoring still runs
        even if individual scrapers fail.
        """
        logger.info("Starting scraper: %s", scraper_name)
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/trigger-scraper/{scraper_name}",
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(
                    "Scraper %s found %d trends",
                    scraper_name,
                    result.get("trends_count", 0),
                )
                return {"scraper": scraper_name, "status": "success", **result}
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Scraper %s returned HTTP %d — continuing gracefully",
                scraper_name,
                exc.response.status_code,
            )
            return {"scraper": scraper_name, "status": "failed", "error": str(exc)}
        except Exception as exc:
            logger.warning(
                "Scraper %s failed: %s — continuing gracefully",
                scraper_name,
                exc,
            )
            return {"scraper": scraper_name, "status": "failed", "error": str(exc)}

    @task(task_id="score_all_trends", trigger_rule="all_done")
    def score_all_trends(scraper_results: list[dict]) -> dict:
        """Score and deduplicate all trends gathered from scrapers."""
        successful = [r for r in scraper_results if r.get("status") == "success"]
        logger.info(
            "Scoring trends from %d/%d successful scrapers",
            len(successful),
            len(scraper_results),
        )

        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{BACKEND_URL}/api/v1/pipeline/score-trends",
                json={"scraper_results": successful},
                headers=DEFAULT_HEADERS,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info("Scored %d trends total", result.get("scored_count", 0))
            return result

    # Dynamic task mapping: one task instance per scraper, running in parallel
    scraper_results = scrape_source.expand(scraper_name=SCRAPERS)
    score_all_trends(scraper_results)


intelligence()
