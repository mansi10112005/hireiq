"""Saves a finished report, and NEVER lets a storage problem destroy the analysis."""

from app.core.database import DatabaseUnavailableError
from app.schemas.analysis import AnalysisReport, StorageSection
from app.services.repository import Repository


def persist_report(
    repo: Repository | None,
    report: AnalysisReport,
    *,
    job_title: str | None,
    job_text: str,
    web_requested: bool,
    web_consented: bool,
) -> tuple[StorageSection, list[str]]:
    """Returns (storage_section, extra_warnings)."""
    if repo is None:
        return StorageSection(stored=False, note="Storage is disabled (STORAGE_ENABLED=false)."), []

    try:
        ids = repo.save_analysis(
            report,
            job_title=job_title,
            job_text=job_text,
            web_requested=web_requested,
            web_consented=web_consented,
        )
    except DatabaseUnavailableError:
        warning = (
            "The analysis could not be saved because the database is not reachable. "
            "The report is complete but was not stored."
        )
        return StorageSection(stored=False, note=warning), [warning]

    return (
        StorageSection(
            stored=True,
            candidate_id=ids.candidate_id,
            job_id=ids.job_id,
            note=(
                "Saved. The original resume file, the full resume text, the phone number and "
                "links are not stored."
            ),
        ),
        [],
    )