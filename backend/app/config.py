"""
app/config.py
─────────────
All runtime configuration sourced from environment variables (or .env file).
Pydantic-Settings validates types at import time, so a misconfigured
deployment fails loudly at startup rather than silently at request time.

AI provider selection
─────────────────────
Set AI_PROVIDER to choose the backend:
  AI_PROVIDER=anthropic  →  uses ANTHROPIC_API_KEY + ANTHROPIC_MODEL
  AI_PROVIDER=qwen       →  uses DASHSCOPE_API_KEY + QWEN_MODEL via the
                             OpenAI-compatible DashScope endpoint

Exactly one provider's API key is required; the other may be omitted.
The app validates this at startup via the Settings.model_post_init hook.

Design note: `get_settings()` is a cached function rather than a bare module
singleton so that tests can monkeypatch settings without affecting other tests.
"""
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "SecureDevIQ"

    # ── AI provider selection ──────────────────────────────────────────────────
    # Choose which LLM backend to use. Only the matching API key is required.
    ai_provider: Literal["anthropic", "qwen", "openrouter"] = "anthropic"

    # ── Anthropic settings (used when ai_provider="anthropic") ─────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ── Qwen / DashScope settings (used when ai_provider="qwen") ──────────────
    # Get a key at: https://www.alibabacloud.com/help/model-studio/get-api-key
    dashscope_api_key: str = ""
    # International endpoint (Singapore/US). China region: dashscope.aliyuncs.com
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    # qwen-plus offers a good balance of quality and speed for this use case.
    # Other options: qwen-max (best), qwen-turbo (fastest/cheapest)
    qwen_model: str = "qwen-plus"

    # ── Openrouter settings (used when ai_provider="openrouter") ───────────────
    # Get a key at: https://openrouter.ai/keys
    openrouter_api_key: str = ""
    # Model to use. Recommended: openai/gpt-4-turbo, claude-3-sonnet, meta-llama/llama-2-70b
    # Full model list: https://openrouter.ai/docs/models
    openrouter_model: str = "openai/gpt-4-turbo"
    # Openrouter endpoint (should not need to change)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

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
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_provider_key(self) -> "Settings":
        """Ensure the API key for the active provider is set."""
        # Prevent accidental startup with insecure fallback secret.
        if self.secret_key == "change-me-in-production-use-openssl-rand-hex-32":
            raise ValueError(
                "SECRET_KEY must be set to a strong random value. "
                "Generate one with: openssl rand -hex 32"
            )
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")

        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "AI_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set."
            )
        if self.ai_provider == "qwen" and not self.dashscope_api_key:
            raise ValueError(
                "AI_PROVIDER=qwen requires DASHSCOPE_API_KEY to be set."
            )
        if self.ai_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError(
                "AI_PROVIDER=openrouter requires OPENROUTER_API_KEY to be set."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call get_settings() everywhere."""
    return Settings()  # type: ignore[call-arg]


# Convenience alias used in places that import at module level
settings = get_settings()
