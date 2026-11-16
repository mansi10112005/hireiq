"""Shared pieces for the API routes."""

from app.core.errors import AppError
from app.schemas.common import ErrorResponse
from app.services.repository import Repository, get_repository

DB_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    503: {"model": ErrorResponse, "description": "Database unavailable or storage disabled"},
}


def require_repository() -> Repository:
    repo = get_repository()
    if repo is None:
        raise AppError(
            "Storage is disabled (STORAGE_ENABLED=false).",
            status_code=503,
            code="storage_disabled",
        )
    return repo