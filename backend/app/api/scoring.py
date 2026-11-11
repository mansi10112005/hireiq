"""Explains how scoring works (the frontend will show this next to every score)."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.scoring import ScoringInfo
from app.services.scoring_config import default_scoring_config, describe_scoring

router = APIRouter(prefix="/scoring", tags=["Scoring"])


@router.get(
    "/config",
    response_model=ScoringInfo,
    summary="Show the default scoring weights, criteria, rules and limitations",
)
def get_scoring_config(settings: Settings = Depends(get_settings)) -> ScoringInfo:
    return describe_scoring(default_scoring_config(settings))