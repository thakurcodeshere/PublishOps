"""
PublishOps — Main Pipeline DAG
================================
Master content pipeline running every 6 hours.
Orchestrates the full content automation flow:
  intelligence → strategy → creation → viral_gate → humanization → redteam → optimizer → compliance → scheduler → synergy_routing

Each task calls the FastAPI backend via httpx.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import httpx
import pendulum
from airflow.decorators import dag, task, task_group
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
    logger.error(
        "Task %s in DAG %s failed: %s",
        task_instance.task_id,
        dag_id,
        error_msg,
    )
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
    dag_id="main_pipeline",
    description="Master content pipeline — intelligence through scheduling and synergy routing",
    schedule="0 */6 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "publishops",
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
        "execution_timeout": timedelta(minutes=45),
        "on_failure_callback": _on_failure,
        "sla": timedelta(hours=2),
    },
    tags=["core", "pipeline"],
)
def main_pipeline():
    """Orchestrate the full content automation pipeline."""

    # ---- Stage 1: Intelligence ----
    @task_group(group_id="intelligence_stage")
    def intelligence_stage():
        @task(task_id="gather_trends")
        def gather_trends() -> dict:
            """Trigger trend intelligence gathering from all sources."""
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/intelligence",
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Intelligence gathered: %d trends found", result.get("trends_count", 0))
                return result

        @task(task_id="score_trends")
        def score_trends(intelligence_data: dict) -> dict:
            """Score and rank discovered trends by virality potential."""
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/score-trends",
                    json=intelligence_data,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Scored %d trends", result.get("scored_count", 0))
                return result

        data = gather_trends()
        return score_trends(data)

    # ---- Stage 2: Strategy ----
    @task_group(group_id="strategy_stage")
    def strategy_stage(scored_trends: dict):
        @task(task_id="generate_strategy")
        def generate_strategy(trends: dict) -> dict:
            """Generate content strategy from scored trends."""
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/strategy",
                    json=trends,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Strategy generated: %d content items planned", result.get("items_count", 0))
                return result

        return generate_strategy(scored_trends)

    # ---- Stage 3: Creation ----
    @task_group(group_id="creation_stage")
    def creation_stage(strategy: dict):
        @task(task_id="create_content")
        def create_content(strategy_data: dict) -> dict:
            """Generate content (scripts, captions, thumbnails) via Claude."""
            with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/create",
                    json=strategy_data,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Content created: %d items", result.get("created_count", 0))
                return result

        return create_content(strategy)

    # ---- Checkpoint: Viral Score Gate ----
    @task_group(group_id="viral_gate_stage")
    def viral_gate_stage(creation_data: dict):
        @task(task_id="check_viral_gate")
        def check_viral_gate(content: dict) -> dict:
            """Verify script virality scores before production assembly."""
            assets = content.get("assets", [])
            for asset in assets:
                brief_id = asset.get("brief_id")
                if not brief_id:
                    continue
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.post(
                        f"{BACKEND_URL}/api/v1/pipeline/viral-gate",
                        json={"brief_id": brief_id},
                        headers=DEFAULT_HEADERS,
                    )
                    resp.raise_for_status()
                    res = resp.json()
                    logger.info("Viral Gate check for brief %s: score=%s, passed=%s", brief_id, res.get("composite_score"), res.get("passed"))
            return content

        return check_viral_gate(creation_data)

    # ---- Stage 4: Humanization ----
    @task_group(group_id="humanization_stage")
    def humanization_stage(content: dict):
        @task(task_id="humanize_content")
        def humanize_content(content_data: dict) -> dict:
            """Apply humanization layer — natural language patterns, personality injection."""
            with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/humanize",
                    json=content_data,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(
                    "Humanization complete — AI score: %.2f",
                    result.get("ai_detection_score", 0.0),
                )
                return result

        return humanize_content(content)

    # ---- Checkpoint: Red-Team Detector ----
    @task_group(group_id="redteam_stage")
    def redteam_stage(humanized_data: dict):
        @task(task_id="check_redteam")
        def check_redteam(content: dict) -> dict:
            """Adversarial check on script and audio files."""
            assets = content.get("humanized", [])
            for asset in assets:
                asset_id = asset.get("id")
                if not asset_id:
                    continue
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.post(
                        f"{BACKEND_URL}/api/v1/pipeline/redteam",
                        json={"asset_id": asset_id},
                        headers=DEFAULT_HEADERS,
                    )
                    resp.raise_for_status()
                    res = resp.json()
                    logger.info("Red-Team check for asset %s: passed=%s", asset_id, res.get("passed"))
            return content

        return check_redteam(humanized_data)

    # ---- Stage 5: Optimizer ----
    @task_group(group_id="optimizer_stage")
    def optimizer_stage(humanized: dict):
        @task(task_id="optimize_content")
        def optimize_content(humanized_data: dict) -> dict:
            """Platform-specific optimization — hooks, hashtags, SEO, thumbnails."""
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/optimize",
                    json=humanized_data,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Optimization complete for %d platforms", result.get("platforms_count", 0))
                return result

        return optimize_content(humanized)

    # ---- Checkpoint: Compliance Disclosure Gate ----
    @task_group(group_id="compliance_stage")
    def compliance_stage(optimized: dict):
        @task(task_id="check_compliance")
        def check_compliance(optimized_data: dict) -> dict:
            """Verify and apply AI disclosure tags before publishing."""
            variants = optimized_data.get("variants", [])
            for variant in variants:
                brief_id = variant.get("brief_id")
                platform = variant.get("platform")
                if not brief_id or not platform:
                    continue
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.post(
                        f"{BACKEND_URL}/api/v1/pipeline/compliance",
                        json={"brief_id": brief_id, "platforms": [platform]},
                        headers=DEFAULT_HEADERS,
                    )
                    resp.raise_for_status()
                    res = resp.json()
                    logger.info("Compliance audit for brief %s on platform %s: status=%s", brief_id, platform, res.get("status"))
            return optimized_data

        return check_compliance(optimized)

    # ---- Stage 6: Scheduler ----
    @task_group(group_id="scheduler_stage")
    def scheduler_stage(optimized: dict):
        @task(task_id="schedule_posts")
        def schedule_posts(optimized_data: dict) -> dict:
            """Schedule optimized posts to optimal time slots and queue uploads."""
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/schedule",
                    json=optimized_data,
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Scheduled %d posts across %d platforms", result.get("scheduled_count", 0), result.get("platforms", 0))
                return result

        return schedule_posts(optimized)

    # ---- Checkpoint: Synergy Routing Gate ----
    @task_group(group_id="synergy_routing_stage")
    def synergy_routing_stage(scheduled: dict):
        @task(task_id="route_synergy")
        def route_synergy(scheduled_data: dict) -> dict:
            """Map cross-platform funnels and UTM campaigns."""
            # Simulated routing triggers
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(
                    f"{BACKEND_URL}/api/v1/pipeline/synergy-routing",
                    json={
                        "platform": "youtube",
                        "destination_url": "https://publishops.io/launch",
                        "base_cta_text": "Join the early access here:"
                    },
                    headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                res = resp.json()
                logger.info("Synergy routing complete: CTA = %s", res.get("cta_text"))
            return scheduled_data

        return route_synergy(scheduled)

    # ---- Wire the pipeline ----
    trends = intelligence_stage()
    strategy = strategy_stage(trends)
    content = creation_stage(strategy)
    gate_checked = viral_gate_stage(content)
    humanized = humanization_stage(gate_checked)
    redteam_checked = redteam_stage(humanized)
    optimized = optimizer_stage(redteam_checked)
    compliance_checked = compliance_stage(optimized)
    scheduled = scheduler_stage(compliance_checked)
    synergy_routing_stage(scheduled)


main_pipeline()
