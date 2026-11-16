"""MongoDB connection and error handling (synchronous PyMongo, safe to share between threads)."""

import logging
from contextlib import contextmanager
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("hireiq")


class DatabaseUnavailableError(AppError):
    """MongoDB could not be reached or refused the operation."""

    def __init__(self) -> None:
        super().__init__(
            "The database is not reachable. Check that MongoDB is running and MONGODB_URI is correct.",
            status_code=503,
            code="database_unavailable",
        )


@contextmanager
def database_errors():
    """Turn any PyMongo failure into one clear error. Logs only the error TYPE, never data."""
    try:
        yield
    except DuplicateKeyError:
        raise  # callers handle this one themselves
    except PyMongoError as exc:
        logger.error("Database error: type=%s", type(exc).__name__)
        raise DatabaseUnavailableError() from None


@lru_cache
def get_client() -> MongoClient:
    """The one shared client. It connects lazily, so creating it never fails at startup."""
    settings = get_settings()
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        tz_aware=True,  # datetimes come back timezone-aware (UTC)
        appname="hireiq",
    )


def get_database() -> Database:
    return get_client()[get_settings().mongodb_db_name]


def close_client() -> None:
    if get_client.cache_info().currsize:
        get_client().close()
        get_client.cache_clear()