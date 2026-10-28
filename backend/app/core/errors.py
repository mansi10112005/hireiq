"""Consistent error responses for the whole API.

Every error returns:
    {"error": {"code": "...", "message": "...", "details": ...}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("hireiq")

# Friendly machine-readable codes for common HTTP statuses.
_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
}


class AppError(Exception):
    """An error we raise ON PURPOSE, with a message that is safe to show the user."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "app_error",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


def _error_response(
    status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, code, message)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # We deliberately report ONLY the field name and the problem.
    # We do NOT echo the submitted value, because later it could be resume text.
    details = [
        {
            "field": ".".join(str(part) for part in err["loc"]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return _error_response(
        422, "validation_error", "The request data is invalid.", details
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full details go to the server log only; the client gets a generic message.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error_response(
        500, "internal_error", "Something went wrong on our side. Please try again."
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)