"""
app/config.py
─────────────
All runtime configuration sourced from environment variables (or .env file).
Pydantic-Settings validates types at import time, so a misconfigured
deployment fails loudly at startup rather than silently at request time.

Design note: `get_settings()` is a cached function rather than a bare module
singleton so that tests can monkeypatch settings without affecting other tests.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "SecureDevIQ"

    # ── Anthropic ──────────────────────────────────────────────────────────────
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str  # postgresql+asyncpg://user:pass@host/db

    # ── Auth (JWT) ─────────────────────────────────────────────────────────────
    # Generate a strong secret: `openssl rand -hex 32`
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call get_settings() everywhere."""
    return Settings()  # type: ignore[call-arg]


# Convenience alias used in places that import at module level
settings = get_settings()
