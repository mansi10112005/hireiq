"""Health-check endpoints: confirm the API (and its database) are alive."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.schemas.common import ErrorResponse, HealthResponse
from app.services.repository import get_repository

router = APIRouter(tags=["Health"])


class DatabaseHealth(BaseModel):
    status: str  # "ok" or "disabled"
    database: str | None = None


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check that the API is running",
)
def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
        integrations={
            "groq_api_key_set": settings.groq_configured,
            "exa_api_key_set": settings.exa_configured,
        },
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealth,
    responses={503: {"model": ErrorResponse, "description": "Database unavailable"}},
    summary="Check that the database is reachable",
)
def database_health(settings: Settings = Depends(get_settings)) -> DatabaseHealth:
    repo = get_repository()
    if repo is None:
        return DatabaseHealth(status="disabled")
    repo.ping()  # raises a clear 503 error if MongoDB is down
    return DatabaseHealth(status="ok", database=settings.mongodb_db_name)