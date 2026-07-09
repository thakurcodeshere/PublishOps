"""PublishOps API — FastAPI application entry point."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import api_router
from backend.config import get_settings
from backend.database import engine
from backend.utils.logger import get_logger, set_request_id, setup_logging
from backend.utils.metrics import setup_metrics

logger = get_logger(__name__)

APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown lifecycle events."""
    settings = get_settings()
    setup_logging()

    # ── Startup ───────────────────────────────────────────────────────────
    logger.info(
        "app_startup",
        database_url=settings.DATABASE_URL.split("@")[-1],  # hide credentials
        redis_url=settings.REDIS_URL,
    )

    # Verify async engine pool is ready by running a simple connection test
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    logger.info("database_pool_ready")

    # Redis connection
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as exc:
        logger.warning("redis_connection_failed", error=str(exc))
        redis_client = None

    app.state.redis = redis_client
    app.state.settings = settings

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    if redis_client is not None:
        await redis_client.aclose()
        logger.info("redis_disconnected")

    await engine.dispose()
    logger.info("database_pool_closed")
    logger.info("app_shutdown_complete")


def create_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="PublishOps API",
        version=APP_VERSION,
        description=(
            "PublishOps content automation platform — discover trending topics, "
            "generate production-ready content, and publish across platforms."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.DEBUG,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")
    setup_metrics(app)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        """Return application health status."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": APP_VERSION,
        }

    # ── Global exception handlers ─────────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "detail": "Internal server error",
                "path": str(request.url),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return app


app = create_application()
