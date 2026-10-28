"""Entry point of the HireIQ backend. Run with: uvicorn app.main:app --reload"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Reminder: never log resume text or request bodies.


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for HireIQ, an AI-assisted recruitment intelligence tool.",
    )

    # CORS: only our own frontend may call this API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1")

    if settings.app_env == "development":
        from app.api import debug  # temporary, see debug.py

        app.include_router(debug.router, prefix="/api/v1")

    return app


app = create_app()