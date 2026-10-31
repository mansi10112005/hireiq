"""The main endpoint: upload a resume + job description, get a full analysis report."""

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.schemas.analysis import AnalysisReport
from app.schemas.common import ErrorResponse
from app.workflows.graph import get_workflow
from app.workflows.state import AnalysisState

logger = logging.getLogger("hireiq")

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.post(
    "",
    response_model=AnalysisReport,
    summary="Analyze a resume against a job description",
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        422: {"model": ErrorResponse, "description": "Invalid input or unreadable document"},
    },
)
async def create_analysis(
    file: UploadFile = File(..., description="A .pdf or .txt resume"),
    job_description: str = Form(..., min_length=30, max_length=20_000),
    job_title: str | None = Form(None, max_length=200),
    enable_web_research: bool = Form(False),
    web_research_consent: bool = Form(
        False, description="Must be true to confirm lawful basis/consent for web research"
    ),
    settings: Settings = Depends(get_settings),
    workflow=Depends(get_workflow),
) -> AnalysisReport:
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
        "warnings": [],
        "completed_nodes": [],
    }

    # The workflow is synchronous; run it in a worker thread so the server stays responsive.
    final_state = await run_in_threadpool(workflow.invoke, initial_state)
    report: AnalysisReport = final_state["report"]

    # Log identifiers and counts only, never resume text or personal data.
    logger.info(
        "Analysis completed: id=%s nodes=%d required_skills=%d",
        report.analysis_id,
        len(report.pipeline),
        len(report.job.required_skills),
    )
    return report