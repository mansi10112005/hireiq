"""Entry point of the HireIQ backend. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api import analyses, candidates, comparisons, health, jobs, resumes, scoring
from app.core.config import get_settings
from app.core.database import DatabaseUnavailableError, close_client
from app.core.errors import register_exception_handlers
from app.services.repository import get_repository

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hireiq")
# Reminder: never log resume text or request bodies.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup and once at shutdown."""
    repo = get_repository()
    if repo is not None:
        try:
            await run_in_threadpool(repo.ensure_indexes)
            logger.info("MongoDB ready: database=%s", settings.mongodb_db_name)
        except DatabaseUnavailableError:
            logger.warning(
                "MongoDB is not reachable at startup. Storage endpoints return 503 until it is."
            )
    yield
    close_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for HireIQ, an AI-assisted recruitment intelligence tool.",
        lifespan=lifespan,
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
    app.include_router(resumes.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(analyses.router, prefix="/api/v1")
    app.include_router(candidates.router, prefix="/api/v1")
    app.include_router(scoring.router, prefix="/api/v1")
    app.include_router(comparisons.router, prefix="/api/v1")

    if settings.app_env == "development":
        from app.api import debug  # temporary, see debug.py

        app.include_router(debug.router, prefix="/api/v1")

    return app


app = create_app()