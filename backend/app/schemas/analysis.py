"""Data shapes produced by the analysis workflow (Milestone 6)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume


class SummaryStatement(BaseModel):
    text: str
    # "resume" = copied from the resume, "derived" = computed by our code, "ai" = written by an LLM
    origin: Literal["resume", "derived", "ai"]
    evidence: list[Evidence] = Field(default_factory=list)


class CandidateSummary(BaseModel):
    generator: str = "template_v0"
    professional_summary: SummaryStatement | None = None
    experience_overview: list[SummaryStatement] = Field(default_factory=list)
    education_overview: list[SummaryStatement] = Field(default_factory=list)
    project_overview: list[SummaryStatement] = Field(default_factory=list)
    key_strengths: list[SummaryStatement] = Field(default_factory=list)


class RelevantEntry(BaseModel):
    section: Literal["experience", "projects"]
    heading: str
    matched_skills: list[str]
    evidence: Evidence


class ExperienceCheck(BaseModel):
    requirement: str
    min_years: int
    stated_years: float | None = None
    status: Literal["meets_stated", "below_stated", "unverified"]
    note: str


class EvaluationResult(BaseModel):
    evaluator: str = "mock_rule_based"
    relevant_entries: list[RelevantEntry] = Field(default_factory=list)
    experience_checks: list[ExperienceCheck] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SkillMatch(BaseModel):
    name: str
    importance: Literal["required", "preferred", "unspecified"]
    status: Literal["supported", "partial", "unverified"]
    evidence: list[Evidence] = Field(default_factory=list, description="Resume evidence")
    requirement_evidence: list[Evidence] = Field(
        default_factory=list, description="Where the job description mentions it"
    )
    note: str


class SkillMatchResult(BaseModel):
    method: str = "basic_v0"
    matches: list[SkillMatch] = Field(default_factory=list)


class WebIntelligenceResult(BaseModel):
    """External information. Always kept separate from resume-based findings."""

    status: Literal["not_requested", "skipped_no_consent", "mock"]
    note: str
    findings: list[str] = Field(default_factory=list)


class ScoreSection(BaseModel):
    status: Literal["not_implemented"] = "not_implemented"
    value: int | None = None
    note: str = (
        "Deterministic scoring is added in Milestone 8. "
        "HireIQ does not rank or reject candidates automatically."
    )


class StorageSection(BaseModel):
    stored: bool = False
    note: str = "Saving reports to the database is added in Milestone 9."


class AnalysisReport(BaseModel):
    analysis_id: str
    created_at: str
    workflow_version: str = "milestone-6-mock"
    job_title: str | None = None
    candidate_name: str | None = None

    resume: ParsedResume
    job: ParsedJobDescription
    summary: CandidateSummary
    evaluation: EvaluationResult
    skill_matches: SkillMatchResult
    unverified_required_skills: list[str] = Field(
        default_factory=list,
        description="Required skills with no evidence in the resume (not proof of absence)",
    )
    interview_questions: list[str] = Field(default_factory=list)

    web_intelligence: WebIntelligenceResult
    score: ScoreSection = Field(default_factory=ScoreSection)
    storage: StorageSection = Field(default_factory=StorageSection)

    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    pipeline: list[str] = Field(default_factory=list, description="Nodes that ran, in order")