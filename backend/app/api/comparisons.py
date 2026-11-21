"""Compare 2-5 saved analyses of the SAME job."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB_RESPONSES, require_repository
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.schemas.comparison import ComparisonResult
from app.schemas.common import ErrorResponse
from app.services.comparison import build_comparison
from app.services.repository import Repository
from app.services.scoring_config import build_scoring_config

router = APIRouter(prefix="/comparisons", tags=["Comparisons"])

MAX_COMPARED = 5


@router.get(
    "",
    response_model=ComparisonResult,
    responses={**DB_RESPONSES, 422: {"model": ErrorResponse, "description": "Invalid selection"}},
    summary="Compare 2-5 analyses of the same job side by side",
)
def compare_analyses(
    analysis_ids: list[str] = Query(
        ..., description="Repeat the parameter: ?analysis_ids=a&analysis_ids=b"
    ),
    weight_required_skills: float | None = Query(None, ge=0, le=100),
    weight_preferred_skills: float | None = Query(None, ge=0, le=100),
    weight_experience: float | None = Query(None, ge=0, le=100),
    weight_projects_qualifications: float | None = Query(None, ge=0, le=100),
    repo: Repository = Depends(require_repository),
    settings: Settings = Depends(get_settings),
) -> ComparisonResult:
    # One common weighting for everyone (validated first, so a bad request costs nothing)
    config = build_scoring_config(
        settings,
        {
            "required_skills": weight_required_skills,
            "preferred_skills": weight_preferred_skills,
            "experience": weight_experience,
            "projects_qualifications": weight_projects_qualifications,
        },
    )

    ids = list(dict.fromkeys(i for i in analysis_ids if 0 < len(i) <= 64))  # unique, keep order
    if len(ids) < 2:
        raise AppError(
            "Select at least two different analyses to compare.",
            status_code=422,
            code="too_few_analyses",
        )
    if len(ids) > MAX_COMPARED:
        raise AppError(
            f"You can compare at most {MAX_COMPARED} analyses at once.",
            status_code=422,
            code="too_many_analyses",
        )

    reports = [repo.get_analysis(analysis_id) for analysis_id in ids]  # 404 if one is missing

    job_ids = {report.storage.job_id for report in reports}
    if len(job_ids) != 1 or None in job_ids:
        raise AppError(
            "Only analyses for the same job can be compared.",
            status_code=422,
            code="different_jobs",
        )

    job = repo.get_job(job_ids.pop())
    return build_comparison(job, reports, config)