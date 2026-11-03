"""The JSON shapes we ask the AI to return. NOT the final report shapes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- Resume extraction ----------
class LLMEntry(_Strict):
    heading: str
    details: list[str]
    date_range: str | None


class LLMSkill(_Strict):
    name: str
    evidence_quote: str


class LLMResumeExtraction(_Strict):
    name: str | None
    email: str | None
    phone: str | None
    summary: str | None
    education: list[LLMEntry]
    experience: list[LLMEntry]
    projects: list[LLMEntry]
    skills: list[LLMSkill]
    certifications: list[str]
    stated_years_of_experience: float | None
    stated_years_quote: str | None


# ---------- Job description extraction ----------
class LLMJobSkill(_Strict):
    name: str
    importance: Literal["required", "preferred", "unspecified"]
    evidence_quote: str


class LLMExperienceRequirement(_Strict):
    min_years: int
    max_years: int | None
    open_ended: bool
    evidence_quote: str


class LLMJobExtraction(_Strict):
    skills: list[LLMJobSkill]
    responsibilities: list[str]
    experience_requirements: list[LLMExperienceRequirement]


# ---------- Candidate summary ----------
class LLMStatement(_Strict):
    text: str
    evidence_quote: str


class LLMSummary(_Strict):
    professional_summary: LLMStatement | None
    key_strengths: list[LLMStatement]
    experience_highlights: list[LLMStatement]
    project_highlights: list[LLMStatement]


# ---------- Evaluation ----------
class LLMRelevantEntry(_Strict):
    section: Literal["experience", "projects"]
    heading: str
    matched_skills: list[str]
    why_relevant: str
    evidence_quote: str


class LLMEvaluation(_Strict):
    relevant_entries: list[LLMRelevantEntry]
    notes: list[str]