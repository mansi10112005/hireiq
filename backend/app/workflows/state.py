"""The shared state passed between workflow nodes."""

import operator
from typing import Annotated, TypedDict

from app.schemas.analysis import (
    AnalysisReport,
    CandidateSummary,
    EvaluationResult,
    SkillMatchResult,
    WebIntelligenceResult,
)
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume


class AnalysisState(TypedDict, total=False):
    # ----- Inputs (provided by the API) -----
    filename: str
    file_bytes: bytes
    job_title: str | None
    job_description: str
    enable_web_research: bool
    web_research_consent: bool

    # ----- Added by nodes -----
    analysis_id: str
    created_at: str
    file_type: str
    resume_text: str
    page_count: int | None
    parsed_resume: ParsedResume
    parsed_job: ParsedJobDescription
    summary: CandidateSummary
    evaluation: EvaluationResult
    skill_matches: SkillMatchResult
    web_result: WebIntelligenceResult
    report: AnalysisReport

    # ----- Lists that ACCUMULATE (operator.add joins the lists instead of overwriting) -----
    warnings: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]