"""Job description endpoints: stateless parsing (Milestone 5) and saved jobs (Milestone 9)."""

import logging

from fastapi import APIRouter, Depends, Query, Response
from starlette.concurrency import run_in_threadpool

from app.api.deps import DB_RESPONSES, require_repository
from app.schemas.common import ErrorResponse
from app.schemas.job import JobDescriptionInput, ParsedJobDescription
from app.schemas.records import JobPage, JobRecord
from app.services.job_ingest import parse_job_for_storage
from app.services.job_parser import parse_job_description
from app.services.repository import Repository

logger = logging.getLogger("hireiq")

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/parse",
    response_model=ParsedJobDescription,
    summary="Extract skills, responsibilities and experience from a job description (not saved)",
    responses={422: {"model": ErrorResponse, "description": "Invalid input"}},
)
async def parse_job(payload: JobDescriptionInput) -> ParsedJobDescription:
    parsed = await run_in_threadpool(parse_job_description, payload.description, payload.title)

    # Log counts only, never the job text.
    logger.info(
        "Job description parsed: chars=%d required=%d preferred=%d other=%d",
        len(payload.description),
        len(parsed.required_skills),
        len(parsed.preferred_skills),
        len(parsed.other_mentioned_skills),
    )
    return parsed


@router.post(
    "",
    response_model=JobRecord,
    status_code=201,
    responses={**DB_RESPONSES, 200: {"model": JobRecord, "description": "Identical job already saved"}},
    summary="Save a job description (identical text is reused)",
)
def create_job(
    payload: JobDescriptionInput,
    response: Response,
    repo: Repository = Depends(require_repository),
) -> JobRecord:
    existing = repo.find_job_by_text(payload.title, payload.description)
    if existing is not None:
        response.status_code = 200
        return existing

    parsed = parse_job_for_storage(payload.title, payload.description)
    job, created = repo.create_job(payload.title, payload.description, parsed)
    response.status_code = 201 if created else 200
    return job


@router.get("", response_model=JobPage, responses=DB_RESPONSES, summary="List saved jobs")
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    repo: Repository = Depends(require_repository),
) -> JobPage:
    items, total = repo.list_jobs(limit, skip)
    return JobPage(items=items, total=total, limit=limit, skip=skip)


@router.get(
    "/{job_id}", response_model=JobRecord, responses=DB_RESPONSES, summary="View a saved job"
)
def get_job(job_id: str, repo: Repository = Depends(require_repository)) -> JobRecord:
    return repo.get_job(job_id)


@router.delete(
    "/{job_id}",
    status_code=204,
    responses=DB_RESPONSES,
    summary="Delete a job (409 if it has analyses, unless cascade=true)",
)
def delete_job(
    job_id: str,
    cascade: bool = Query(False, description="Also delete the job's analyses"),
    repo: Repository = Depends(require_repository),
) -> None:
    repo.delete_job(job_id, cascade=cascade)