"""Analyses: create (run the workflow and save), list history, view one, delete."""

import logging

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import DB_RESPONSES, require_repository
from app.core.config import Settings, get_settings
from app.core.database import DatabaseUnavailableError
from app.core.errors import AppError
from app.schemas.analysis import AnalysisReport
from app.schemas.common import ErrorResponse
from app.schemas.records import AnalysisPage
from app.services.repository import Repository, get_repository
from app.services.scoring_config import build_scoring_config
from app.services.report_export import export_report_json, export_report_pdf
from app.workflows.graph import get_workflow
from app.workflows.state import AnalysisState

logger = logging.getLogger("hireiq")

router = APIRouter(prefix="/analyses", tags=["Analyses"])

_WEIGHT_HELP = "Optional. Relative weight (0-100); weights are scaled to add up to 100."


@router.post(
    "",
    response_model=AnalysisReport,
    summary="Analyze a resume against a job description (and save the result)",
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        422: {"model": ErrorResponse, "description": "Invalid input or unreadable document"},
        **{k: v for k, v in DB_RESPONSES.items() if k in (404, 503)},
    },
)
async def create_analysis(
    file: UploadFile = File(..., description="A .pdf or .txt resume"),
    job_description: str | None = Form(
        None, min_length=30, max_length=20_000, description="Paste the job text, OR use job_id"
    ),
    job_id: str | None = Form(None, max_length=64, description="Id of a saved job, OR use job_description"),
    job_title: str | None = Form(None, max_length=200),
    save_result: bool = Form(True, description="False = do not store this analysis at all"),
    enable_web_research: bool = Form(False),
    web_research_consent: bool = Form(
        False, description="Must be true to confirm lawful basis/consent for web research"
    ),
    weight_required_skills: float | None = Form(None, ge=0, le=100, description=_WEIGHT_HELP),
    weight_preferred_skills: float | None = Form(None, ge=0, le=100, description=_WEIGHT_HELP),
    weight_experience: float | None = Form(None, ge=0, le=100, description=_WEIGHT_HELP),
    weight_projects_qualifications: float | None = Form(
        None, ge=0, le=100, description=_WEIGHT_HELP
    ),
    settings: Settings = Depends(get_settings),
    workflow=Depends(get_workflow),
) -> AnalysisReport:
    if (job_description is None) == (job_id is None):
        raise AppError(
            "Provide either job_description or job_id, but not both.",
            status_code=422,
            code="invalid_job_input",
        )

    # Validate the scoring weights FIRST, so a bad request costs nothing (no AI calls).
    scoring_config = build_scoring_config(
        settings,
        {
            "required_skills": weight_required_skills,
            "preferred_skills": weight_preferred_skills,
            "experience": weight_experience,
            "projects_qualifications": weight_projects_qualifications,
        },
    )

    parsed_job = None  # set when we can reuse saved requirements (same criteria for everyone)
    storage_note: str | None = None
    initial_warnings: list[str] = []

    if job_id is not None:
        repo = require_repository()
        job = await run_in_threadpool(repo.get_job, job_id)  # 404 if unknown, 503 if DB is down
        job_description, job_title, parsed_job = job.description, job.title, job.parsed
    elif save_result:
        repo = get_repository()
        if repo is not None:
            try:
                existing = await run_in_threadpool(repo.find_job_by_text, job_title, job_description)
            except DatabaseUnavailableError:
                save_result = False
                storage_note = "The database was not reachable, so this analysis was not saved."
                initial_warnings.append(storage_note)
            else:
                if existing is not None:
                    parsed_job = existing.parsed

    # Read at most limit+1 bytes; node 1 of the workflow does the real validation.
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)

    initial_state: AnalysisState = {
        "filename": file.filename or "",
        "file_bytes": data,
        "job_title": job_title,
        "job_description": job_description,
        "enable_web_research": enable_web_research,
        "web_research_consent": web_research_consent,
        "scoring_config": scoring_config,
        "save_result": save_result,
        "warnings": initial_warnings,
        "completed_nodes": [],
    }
    if parsed_job is not None:
        initial_state["parsed_job"] = parsed_job
    if storage_note is not None:
        initial_state["storage_note"] = storage_note

    # The workflow is synchronous; run it in a worker thread so the server stays responsive.
    final_state = await run_in_threadpool(workflow.invoke, initial_state)
    report: AnalysisReport = final_state["report"]

    # Log identifiers and counts only, never resume text or personal data.
    logger.info(
        "Analysis completed: id=%s nodes=%d required_skills=%d score=%s stored=%s",
        report.analysis_id,
        len(report.pipeline),
        len(report.job.required_skills),
        report.score.value,
        report.storage.stored,
    )
    return report


@router.get(
    "",
    response_model=AnalysisPage,
    responses=DB_RESPONSES,
    summary="History: list saved analyses, newest first",
)
def list_analyses(
    job_id: str | None = Query(None, description="Only analyses for this job"),
    candidate_id: str | None = Query(None, description="Only analyses for this candidate"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    repo: Repository = Depends(require_repository),
) -> AnalysisPage:
    items, total = repo.list_analyses(job_id=job_id, candidate_id=candidate_id, limit=limit, skip=skip)
    return AnalysisPage(items=items, total=total, limit=limit, skip=skip)


@router.get(
    "/{analysis_id}",
    response_model=AnalysisReport,
    responses=DB_RESPONSES,
    summary="View a saved analysis (the full report)",
)
def get_analysis(analysis_id: str, repo: Repository = Depends(require_repository)) -> AnalysisReport:
    return repo.get_analysis(analysis_id)


@router.delete(
    "/{analysis_id}",
    status_code=204,
    responses=DB_RESPONSES,
    summary="Delete an analysis (and the candidate, if it was their last one)",
)
def delete_analysis(analysis_id: str, repo: Repository = Depends(require_repository)) -> None:
    repo.delete_analysis(analysis_id)

@router.get(
    "/{analysis_id}/export",
    response_class=Response,
    responses=DB_RESPONSES,
    summary="Download a saved report as PDF or JSON",
)
def export_analysis(
    analysis_id: str,
    file_format: Literal["pdf", "json"] = Query("pdf", alias="format"),
    repo: Repository = Depends(require_repository),
) -> Response:
    report = repo.get_analysis(analysis_id)

    if file_format == "json":
        content, media_type = export_report_json(report), "application/json"
    else:
        content, media_type = export_report_pdf(report), "application/pdf"

    # The file name uses only the id (never a person's name): no personal data in headers.
    filename = f"hireiq-report-{report.analysis_id[:8]}.{file_format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",  # reports contain personal data
            "X-Content-Type-Options": "nosniff",
        },
    )