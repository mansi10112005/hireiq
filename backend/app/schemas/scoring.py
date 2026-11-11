"""Data shapes for scoring: configuration, the score breakdown, and the public rules."""

from typing import Literal

from pydantic import BaseModel, Field

ComponentKey = Literal[
    "required_skills", "preferred_skills", "experience", "projects_qualifications"
]


class ScoringWeights(BaseModel):
    """Relative importance of each criterion. They are scaled to add up to 100."""

    required_skills: float = Field(ge=0, le=100)
    preferred_skills: float = Field(ge=0, le=100)
    experience: float = Field(ge=0, le=100)
    projects_qualifications: float = Field(ge=0, le=100)


class ScoringConfig(BaseModel):
    weights: ScoringWeights
    partial_credit: float = Field(ge=0, le=1, description="Credit for skills only listed in Skills")
    entries_for_full_credit: int = Field(ge=1, le=10)


class ScoreComponent(BaseModel):
    key: ComponentKey
    label: str
    applicable: bool = Field(description="False when the job description gives no data for it")
    fraction: float | None = Field(
        None, description="0.0 to 1.0: how much of the criterion is evidenced"
    )
    configured_weight: float = Field(description="Weight after scaling to add up to 100")
    effective_weight: float = Field(
        description="Weight actually used after sharing out the weights of unused criteria"
    )
    points: float = Field(description="fraction x effective_weight")
    explanation: str
    details: list[str] = Field(default_factory=list)


class ScoreSection(BaseModel):
    status: Literal["calculated", "not_calculated"]
    value: int | None = Field(None, ge=1, le=100)
    exact: float | None = Field(None, description="The unrounded score")
    evidence_level: Literal["strong", "moderate", "limited"] | None = Field(
        None,
        description="strong: 75+, moderate: 50-74, limited: below 50. Descriptive, not a decision.",
    )
    method: str
    weights: ScoringWeights = Field(description="The configured weights, scaled to add up to 100")
    partial_credit: float
    entries_for_full_credit: int
    components: list[ScoreComponent] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    disclaimer: str


class ComponentInfo(BaseModel):
    key: ComponentKey
    label: str
    description: str


class ScoringInfo(BaseModel):
    method: str
    weights: ScoringWeights
    partial_credit: float
    entries_for_full_credit: int
    components: list[ComponentInfo]
    rules: list[str]
    limitations: list[str]