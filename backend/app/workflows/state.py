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
from app.schemas.scoring import ScoringConfig


class AnalysisState(TypedDict, total=False):
    # ----- Inputs (provided by the API) -----
    filename: str
    file_bytes: bytes
    job_title: str | None
    job_description: str
    enable_web_research: bool
    web_research_consent: bool
    scoring_config: ScoringConfig  # optional; defaults come from settings

    save_result: bool  # False = do not store this analysis
    storage_note: str  # why saving was skipped (set by the API)

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
    ai_nodes_used: Annotated[list[str], operator.add]
    ai_fallbacks: Annotated[list[str], operator.add]