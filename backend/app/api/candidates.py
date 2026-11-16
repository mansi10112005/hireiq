"""Stored candidates: list, view, and delete (right to erasure)."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB_RESPONSES, require_repository
from app.schemas.records import CandidatePage, CandidateRecord
from app.services.repository import Repository

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=CandidatePage, responses=DB_RESPONSES, summary="List candidates")
def list_candidates(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    repo: Repository = Depends(require_repository),
) -> CandidatePage:
    items, total = repo.list_candidates(limit, skip)
    return CandidatePage(items=items, total=total, limit=limit, skip=skip)


@router.get(
    "/{candidate_id}",
    response_model=CandidateRecord,
    responses=DB_RESPONSES,
    summary="View a candidate and their analyses",
)
def get_candidate(
    candidate_id: str, repo: Repository = Depends(require_repository)
) -> CandidateRecord:
    return repo.get_candidate(candidate_id)


@router.delete(
    "/{candidate_id}",
    status_code=204,
    responses=DB_RESPONSES,
    summary="Delete a candidate AND all of their analyses",
)
def delete_candidate(candidate_id: str, repo: Repository = Depends(require_repository)) -> None:
    repo.delete_candidate(candidate_id)