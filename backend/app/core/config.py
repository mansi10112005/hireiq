"""Application settings, loaded once from environment variables / the .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] is the "backend" folder.
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _is_real_value(value: str | None) -> bool:
    """True if a secret looks filled in (not empty and not a placeholder)."""
    return bool(value) and not value.startswith("your_") and not value.startswith("paste_")


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

    # Resume upload limits (Milestone 4)
    max_upload_size_mb: int = 5
    max_pdf_pages: int = 15
    max_resume_chars: int = 50_000
    min_resume_chars: int = 50

    # Groq AI (Milestone 7)
    groq_api_key: str | None = None
    llm_enabled: bool = True
    groq_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: str | None = "low"
    groq_strict_schema: bool = False
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 3
    llm_max_resume_chars: int = 12_000  # how much resume text we send to the AI
    llm_max_job_chars: int = 6_000  # how much job text we send to the AI

    # Scoring (Milestone 8): weights are relative and are scaled to add up to 100
    score_weight_required_skills: float = 50
    score_weight_preferred_skills: float = 15
    score_weight_experience: float = 20
    score_weight_projects_qualifications: float = 15
    score_partial_credit: float = 0.5
    score_entries_for_full_credit: int = 2

    # Storage (Milestone 9)
    storage_enabled: bool = True
    mongodb_timeout_ms: int = 3000  # how long to wait for the database before giving up
    retention_days: int = 0  # 0 = keep until deleted; N = records expire N days after the last analysis

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