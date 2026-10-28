"""TEMPORARY routes to test error handling. Only loaded when APP_ENV=development.
Remove this file (and its line in main.py) before deployment."""

from fastapi import APIRouter

from app.core.errors import AppError

router = APIRouter(prefix="/debug", tags=["Debug (development only)"])


@router.get("/app-error")
def trigger_app_error():
    raise AppError("This is a demo of a handled error.", status_code=400, code="demo_error")


@router.get("/crash")
def trigger_crash():
    raise RuntimeError("secret internal detail that users must never see")


@router.get("/validate")
def trigger_validation(limit: int):
    return {"limit": limit}