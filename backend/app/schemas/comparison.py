"""Response shapes for the side-by-side comparison."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.scoring import ScoreComponent, ScoringWeights

Status = Literal["supported", "partial", "unverified"]


class ComparedCandidate(BaseModel):
    analysis_id: str
    candidate_id: str | None = None
    candidate_name: str | None = None
    analysed_at: str
    score: int | None = None
    evidence_level: Literal["strong", "moderate", "limited"] | None = None
    stored_score: int | None = Field(None, description="The score in the original report")
    score_changed: bool = Field(
        description="True if the common criteria gave a different score than the original report"
    )
    components: list[ScoreComponent]
    required_supported: int
    required_partial: int
    required_total: int


class SkillComparisonRow(BaseModel):
    name: str
    importance: Literal["required", "preferred", "unspecified"]
    statuses: list[Status] = Field(description="One status per candidate, in the same order")


class ComparisonScoring(BaseModel):
    method: str
    weights: ScoringWeights = Field(description="Scaled to add up to 100")
    partial_credit: float
    entries_for_full_credit: int


class ComparisonResult(BaseModel):
    job_id: str
    job_title: str | None = None
    scoring: ComparisonScoring
    candidates: list[ComparedCandidate]  # in the order the user selected, NOT sorted by score
    skills: list[SkillComparisonRow]
    notes: list[str]
    disclaimer: str