"""Data shapes for job descriptions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import Evidence


class JobDescriptionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, max_length=200)
    description: str = Field(min_length=30, max_length=20_000)


class JobSkill(BaseModel):
    name: str
    importance: Literal["required", "preferred", "unspecified"]
    evidence: list[Evidence] = Field(default_factory=list)


class ExperienceRequirement(BaseModel):
    min_years: int
    max_years: int | None = None
    open_ended: bool = Field(description="True for wording like '3+ years'")
    evidence: Evidence


class ParsedJobDescription(BaseModel):
    parser: str = "rule_based_v1"
    title: str | None = None
    required_skills: list[JobSkill] = Field(default_factory=list)
    preferred_skills: list[JobSkill] = Field(default_factory=list)
    other_mentioned_skills: list[JobSkill] = Field(
        default_factory=list,
        description="Mentioned, but the text does not say whether required or preferred",
    )
    responsibilities: list[str] = Field(default_factory=list)
    experience_requirements: list[ExperienceRequirement] = Field(default_factory=list)
    sections_found: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)