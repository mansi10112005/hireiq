"""Job description endpoints. (Saving jobs to the database comes in Milestone 9.)"""

import logging

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.common import ErrorResponse
from app.schemas.job import JobDescriptionInput, ParsedJobDescription
from app.services.job_parser import parse_job_description

logger = logging.getLogger("hireiq")

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/parse",
    response_model=ParsedJobDescription,
    summary="Extract required/preferred skills, responsibilities and experience from a job description",
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