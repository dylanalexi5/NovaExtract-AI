"""
Centralized application configuration settings.

Uses pydantic-settings to load environment variables with startup type validation.
If a required variable is missing, the application fails fast.
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings injectable via Depends(get_settings)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignores undeclared environment variables
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "DevTalenty AI Extractor"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Hybrid data extraction API for CVs using Rules + AI with Instructor and Pydantic v2."
    )
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ── Database (Supabase / PostgreSQL) ─────────────────────────────────
    DATABASE_URL: PostgresDsn

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Returns the asyncpg-compatible database URL."""
        return str(self.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")

    # ── External LLM (OpenAI / Groq) ─────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str | None = None

    # ── Environment ──────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"  # development | staging | production


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton instance of Settings.

    @lru_cache prevents re-reading the .env file on every request.
    Can be cleared in unit tests using get_settings.cache_clear().
    """
    return Settings()  # type: ignore[call-arg]
