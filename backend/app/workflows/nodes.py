"""The nine workflow nodes.

Rules for every node:
  - it receives the shared state
  - it returns ONLY the keys it adds or changes
  - fatal problems raise AppError; non-fatal ones go into "warnings"
  - it never logs resume text
"""

import functools
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from app.core.config import get_settings
from app.schemas.analysis import WebIntelligenceResult
from app.services.evaluator import evaluate_candidate
from app.services.job_parser import parse_job_description
from app.services.report_builder import build_report
from app.services.resume_parser import parse_resume
from app.services.skill_matcher import match_skills
from app.services.summary_builder import build_candidate_summary
from app.services.text_extraction import extract_text
from app.utils.file_validation import validate_upload_bytes
from app.workflows.state import AnalysisState

logger = logging.getLogger("hireiq")


class WorkflowStateError(RuntimeError):
    """A node ran without the state it needs. This is a programming error, not a user error."""


def node_step(name: str, requires: tuple[str, ...] = ()) -> Callable:
    """Wrap a node: check required inputs, log timing (no content), record completion."""

    def decorator(func: Callable[[AnalysisState], dict]) -> Callable[[AnalysisState], dict]:
        @functools.wraps(func)
        def wrapper(state: AnalysisState) -> dict:
            missing = [key for key in requires if state.get(key) is None]
            if missing:
                raise WorkflowStateError(
                    f"Node '{name}' is missing required state: {', '.join(missing)}"
                )
            started = time.perf_counter()
            update = func(state)
            update["completed_nodes"] = [name]
            logger.info(
                "Workflow node finished: node=%s ms=%d",
                name,
                int((time.perf_counter() - started) * 1000),
            )
            return update

        return wrapper

    return decorator


# 1) Resume Upload: validate the document and create the analysis request
@node_step("resume_upload", requires=("filename", "file_bytes"))
def resume_upload_node(state: AnalysisState) -> dict:
    upload = validate_upload_bytes(state["filename"], state["file_bytes"], get_settings())
    return {
        "analysis_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": upload.filename,
        "file_type": upload.file_type,
    }


# 2) Text Extraction: read the text, then drop the raw file bytes from the state
@node_step("text_extraction", requires=("file_bytes", "file_type"))
def text_extraction_node(state: AnalysisState) -> dict:
    result = extract_text(state["file_bytes"], state["file_type"], get_settings())
    return {
        "resume_text": result.text,
        "page_count": result.page_count,
        "warnings": result.warnings,
        "file_bytes": b"",  # we no longer need the original file
    }


# 3) CV Parsing: resume text -> validated structured fields
@node_step("cv_parsing", requires=("resume_text",))
def cv_parsing_node(state: AnalysisState) -> dict:
    return {"parsed_resume": parse_resume(state["resume_text"])}


# 4) Job Description Skill Extraction
@node_step("jd_skill_extraction", requires=("job_description",))
def jd_skill_extraction_node(state: AnalysisState) -> dict:
    return {"parsed_job": parse_job_description(state["job_description"], state.get("job_title"))}


# 5) Candidate Summary (resume-only, template-based for now)
@node_step("candidate_summary", requires=("parsed_resume",))
def candidate_summary_node(state: AnalysisState) -> dict:
    return {"summary": build_candidate_summary(state["parsed_resume"])}


# 6) AI Evaluation (MOCK, rule-based; the LLM version arrives in Milestone 7)
@node_step("ai_evaluation", requires=("parsed_resume", "parsed_job"))
def ai_evaluation_node(state: AnalysisState) -> dict:
    return {"evaluation": evaluate_candidate(state["parsed_resume"], state["parsed_job"])}


# 7) Skills Matching (BASIC; Milestone 8 improves it)
@node_step("skills_matching", requires=("parsed_resume", "parsed_job"))
def skills_matching_node(state: AnalysisState) -> dict:
    return {"skill_matches": match_skills(state["parsed_resume"], state["parsed_job"])}


# Router for the conditional edge: is web research allowed AND consented to?
def route_after_matching(state: AnalysisState) -> str:
    if state.get("enable_web_research") and state.get("web_research_consent"):
        return "web_intelligence"
    return "score_and_store"


# 8) Web Intelligence (MOCK adapter: performs NO real search)
@node_step("web_intelligence")
def web_intelligence_node(state: AnalysisState) -> dict:
    return {
        "web_result": WebIntelligenceResult(
            status="mock",
            note="Mock adapter: no real web search was performed. "
            "Real research (Exa) is added in Milestone 13.",
        )
    }


# 9) Score Decision and Storage (score and storage are placeholders for now)
@node_step("score_and_store", requires=("parsed_resume", "parsed_job", "skill_matches"))
def score_and_store_node(state: AnalysisState) -> dict:
    report = build_report(
        analysis_id=state["analysis_id"],
        created_at=state["created_at"],
        job_title=state.get("job_title"),
        resume=state["parsed_resume"],
        job=state["parsed_job"],
        summary=state["summary"],
        evaluation=state["evaluation"],
        skill_matches=state["skill_matches"],
        web=state.get("web_result"),
        web_requested=bool(state.get("enable_web_research")),
        warnings=state.get("warnings", []),
        completed_nodes=state.get("completed_nodes", []),
    )
    return {"report": report}