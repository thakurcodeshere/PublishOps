"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for PublishOps backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "PublishOps"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database / Cache ──────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/publishops"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── API Keys ──────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    RUNWAY_API_KEY: str = ""
    BANNERBEAR_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    BUZZSUMO_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    NEWSAPI_KEY: str = ""
    PEXELS_API_KEY: str = ""
    SEMRUSH_API_KEY: str = ""

    # ── AWS / S3 ──────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "publishops-assets"
    AWS_REGION: str = "us-east-1"

    # ── ElevenLabs ────────────────────────────────────────────────────────
    ELEVENLABS_VOICE_ID: str = ""

    # ── Scoring defaults ──────────────────────────────────────────────────
    VELOCITY_WEIGHT: float = Field(default=0.4)
    EVERGREEN_WEIGHT: float = Field(default=0.3)
    FIT_WEIGHT: float = Field(default=0.2)
    SATURATION_WEIGHT: float = Field(default=0.1)
    MIN_SCORE_THRESHOLD: int = 65
    MAX_SATURATION: float = 0.8

    # ── Reddit OAuth ──────────────────────────────────────────────────────
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "PublishOps/1.0"

    # ── Auphonic ──────────────────────────────────────────────────────────
    AUPHONIC_API_KEY: str = ""

    # ── LinkedIn ──────────────────────────────────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = ""

    # ── TikTok ────────────────────────────────────────────────────────────
    TIKTOK_ACCESS_TOKEN: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
