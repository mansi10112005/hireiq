"""Application settings, loaded once from environment variables / the .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] is the "backend" folder.
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _is_real_value(value: str | None) -> bool:
    """True if a secret looks filled in (not empty and not a placeholder)."""
    return bool(value) and not value.startswith("your_")


class Settings(BaseSettings):
    """All configuration for the backend. Field names match .env keys (case-insensitive)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown variables instead of crashing
    )

    # App
    app_name: str = "HireIQ API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"

    # Groq (used from Milestone 7)
    groq_api_key: str | None = None

    # MongoDB (used from Milestone 9)
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "hireiq"

    # Optional web research (Milestone 13)
    exa_api_key: str | None = None

    @property
    def groq_configured(self) -> bool:
        return _is_real_value(self.groq_api_key)

    @property
    def exa_configured(self) -> bool:
        return _is_real_value(self.exa_api_key)


@lru_cache
def get_settings() -> Settings:
    """Create the Settings object once and reuse it (lru_cache remembers the result)."""
    return Settings()