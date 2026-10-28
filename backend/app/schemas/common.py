"""Shared response shapes (Pydantic models). They also feed the Swagger docs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    timestamp: datetime
    # Reports whether a key is SET, not whether it WORKS. Never shows the key.
    integrations: dict[str, bool]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorBody