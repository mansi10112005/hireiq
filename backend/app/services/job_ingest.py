"""Parses a job description for saving: rule-based, plus AI when available (never fails)."""

import logging

from app.core.config import get_settings
from app.schemas.job import ParsedJobDescription
from app.services.job_parser import parse_job_description
from app.services.llm_client import get_llm_client
from app.services.llm_job import enhance_job
from app.services.text_extraction import normalize_text

logger = logging.getLogger("hireiq")


def parse_job_for_storage(title: str | None, text: str) -> ParsedJobDescription:
    base = parse_job_description(text, title)
    llm = get_llm_client()
    if llm is None:
        return base
    try:
        parsed, _notes = enhance_job(
            llm, normalize_text(text), base, get_settings().llm_max_job_chars
        )
        return parsed
    except Exception as exc:  # noqa: BLE001
        # Log only the type: the message could contain job text.
        logger.warning("AI job parsing failed (%s); using rule-based result", type(exc).__name__)
        return base