"""Response shapes for stored jobs, candidates and analyses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.job import ParsedJobDescription


# ---------- Jobs ----------
class JobSummary(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    required_skill_count: int
    preferred_skill_count: int
    analysis_count: int


class JobRecord(JobSummary):
    description: str  # the original job text, kept for verification
    parsed: ParsedJobDescription


class JobPage(BaseModel):
    items: list[JobSummary]
    total: int
    limit: int
    skip: int


# ---------- Analyses ----------
class AnalysisSummary(BaseModel):
    id: str
    created_at: datetime
    candidate_id: str
    candidate_name: str | None = None
    job_id: str
    job_title: str | None = None
    score: int | None = None
    evidence_level: Literal["strong", "moderate", "limited"] | None = None
    ai_used: bool = False


class AnalysisPage(BaseModel):
    items: list[AnalysisSummary]
    total: int
    limit: int
    skip: int


# ---------- Candidates ----------
class CandidateSummary(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    analysis_count: int
    first_seen_at: datetime
    last_analysis_at: datetime


class CandidateRecord(CandidateSummary):
    analyses: list[AnalysisSummary]


class CandidatePage(BaseModel):
    items: list[CandidateSummary]
    total: int
    limit: int
    skip: int