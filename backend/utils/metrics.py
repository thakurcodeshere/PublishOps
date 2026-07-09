"""Prometheus client integration for tracking pipeline metrics and latency."""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# ── Metrics Definitions ───────────────────────────────────────────────────

# Pipeline executions
PIPELINE_RUNS_TOTAL = Counter(
    "publishops_pipeline_runs_total",
    "Total number of content pipeline executions.",
    ["trigger"]  # manual, scheduled
)

# Pipeline stage completions
PIPELINE_STAGE_COMPLETIONS_TOTAL = Counter(
    "publishops_pipeline_stage_completions_total",
    "Total number of completed pipeline stages.",
    ["stage", "status"]  # intelligence, strategy, ..., status=completed/failed
)

# Latency per stage
PIPELINE_STAGE_LATENCY_SECONDS = Histogram(
    "publishops_pipeline_stage_latency_seconds",
    "Time taken to complete each pipeline stage in seconds.",
    ["stage"]
)

# API Spend tracking
API_SPEND_USD_TOTAL = Counter(
    "publishops_api_spend_usd_total",
    "Cumulative spending on downstream paid APIs in USD.",
    ["service"]  # anthropic, elevenlabs, gptzero
)

# Pipeline Queue Depth
QUEUE_DEPTH = Gauge(
    "publishops_queue_depth",
    "Current number of posts pending in the scheduled upload queue.",
    ["platform"]
)

# Service Latency
EXTERNAL_SERVICE_LATENCY_MS = Gauge(
    "publishops_external_service_latency_ms",
    "Latency of external service pings in milliseconds.",
    ["service"]
)


def setup_metrics(app: FastAPI) -> None:
    """Mount the Prometheus metrics ASGI application as a sub-app under /metrics."""
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
