"""The nine workflow nodes.

Rules for every node:
  - it receives the shared state
  - it returns ONLY the keys it adds or changes
  - fatal problems raise AppError; non-fatal ones go into "warnings"
  - AI and storage problems NEVER stop the workflow
  - it never logs resume text
"""

import functools
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.config import get_settings
from app.schemas.analysis import StorageSection, WebIntelligenceResult
from app.services.evaluator import evaluate_candidate
from app.services.evidence_validation import validate_match_evidence
from app.services.injection_check import injection_warning, looks_like_prompt_injection
from app.services.job_parser import parse_job_description
from app.services.llm_client import LLMUnavailableError, get_llm_client
from app.services.llm_evaluation import evaluate_with_llm
from app.services.llm_job import enhance_job
from app.services.llm_resume import enhance_resume
from app.services.llm_summary import summarize_with_llm
from app.services.persistence import persist_report
from app.services.report_builder import build_report
from app.services.repository import get_repository
from app.services.resume_parser import parse_resume
from app.services.scoring import calculate_score
from app.services.scoring_config import default_scoring_config
from app.services.skill_matcher import match_skills
from app.services.summary_builder import build_candidate_summary
from app.services.text_extraction import extract_text, normalize_text
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


def _run_ai_step(
    node: str,
    llm: Any,
    ai_call: Callable[[], tuple[Any, list[str]]],
    fallback_call: Callable[[], Any],
) -> tuple[Any, dict]:
    """Try the AI version; on ANY problem use the rule-based version instead.

    Returns (result, extra_state_updates).
    """
    if llm is None:  # AI is switched off or not configured: not an error
        return fallback_call(), {}
    try:
        result, notes = ai_call()
        return result, {"ai_nodes_used": [node], "warnings": notes}
    except LLMUnavailableError as exc:
        reason = str(exc)  # safe: never contains document text
    except Exception as exc:  # noqa: BLE001
        # Log only the TYPE: the message of an unexpected error could contain resume text.
        logger.error("Unexpected AI step error: node=%s type=%s", node, type(exc).__name__)
        reason = "unexpected error"
    logger.warning("AI step fell back to rules: node=%s", node)
    return fallback_call(), {
        "ai_fallbacks": [node],
        "warnings": [f"The AI step '{node}' failed ({reason}); the rule-based result was used instead."],
    }


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
    warnings = list(result.warnings)
    if looks_like_prompt_injection(result.text):
        warnings.append(injection_warning("resume"))
    return {
        "resume_text": result.text,
        "page_count": result.page_count,
        "warnings": warnings,
        "file_bytes": b"",  # we no longer need the original file
    }


# 3) CV Parsing: rule-based baseline, enhanced by the AI when available
@node_step("cv_parsing", requires=("resume_text",))
def cv_parsing_node(state: AnalysisState) -> dict:
    text = state["resume_text"]
    base = parse_resume(text)
    llm = get_llm_client()
    parsed, extra = _run_ai_step(
        "cv_parsing",
        llm,
        lambda: enhance_resume(llm, text, base, get_settings().llm_max_resume_chars),
        lambda: base,
    )
    return {"parsed_resume": parsed, **extra}


# 4) Job Description Skill Extraction: reuse saved requirements, or parse (rules + AI)
@node_step("jd_skill_extraction", requires=("job_description",))
def jd_skill_extraction_node(state: AnalysisState) -> dict:
    job_text = normalize_text(state["job_description"])
    warnings: list[str] = []
    if looks_like_prompt_injection(job_text):
        warnings.append(injection_warning("job description"))

    reused = state.get("parsed_job")
    if reused is not None:  # saved earlier: same criteria for every candidate, no AI cost
        warnings.append(
            "The job requirements were reused from a saved job description, so every candidate "
            "is scored against the same criteria."
        )
        return {"parsed_job": reused, "warnings": warnings}

    base = parse_job_description(state["job_description"], state.get("job_title"))
    llm = get_llm_client()
    parsed, extra = _run_ai_step(
        "jd_skill_extraction",
        llm,
        lambda: enhance_job(llm, job_text, base, get_settings().llm_max_job_chars),
        lambda: base,
    )
    warnings = list(extra.pop("warnings", [])) + warnings
    return {"parsed_job": parsed, "warnings": warnings, **extra}


# 5) Candidate Summary: AI statements with verified quotes, template as fallback
@node_step("candidate_summary", requires=("parsed_resume", "resume_text"))
def candidate_summary_node(state: AnalysisState) -> dict:
    resume = state["parsed_resume"]
    text = state["resume_text"]
    llm = get_llm_client()
    summary, extra = _run_ai_step(
        "candidate_summary",
        llm,
        lambda: summarize_with_llm(llm, resume, text),
        lambda: build_candidate_summary(resume),
    )
    return {"summary": summary, **extra}


# 6) AI Evaluation: AI explanations (verified), rule-based as fallback
@node_step("ai_evaluation", requires=("parsed_resume", "parsed_job", "resume_text"))
def ai_evaluation_node(state: AnalysisState) -> dict:
    resume = state["parsed_resume"]
    job = state["parsed_job"]
    text = state["resume_text"]
    llm = get_llm_client()
    evaluation, extra = _run_ai_step(
        "ai_evaluation",
        llm,
        lambda: evaluate_with_llm(llm, resume, job, text),
        lambda: evaluate_candidate(resume, job),
    )
    return {"evaluation": evaluation, **extra}


# 7) Skills Matching: deterministic matching, then every piece of evidence is VERIFIED
@node_step(
    "skills_matching",
    requires=("parsed_resume", "parsed_job", "resume_text", "job_description"),
)
def skills_matching_node(state: AnalysisState) -> dict:
    matches = match_skills(state["parsed_resume"], state["parsed_job"])
    validated, notes = validate_match_evidence(
        matches, state["resume_text"], normalize_text(state["job_description"])
    )
    return {"skill_matches": validated, "warnings": notes}


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


# 9) Score Decision and Storage: calculate the score, assemble the report, save it
@node_step(
    "score_and_store",
    requires=("parsed_resume", "parsed_job", "skill_matches", "job_description"),
)
def score_and_store_node(state: AnalysisState) -> dict:
    llm = get_llm_client()
    config = state.get("scoring_config") or default_scoring_config(get_settings())
    score = calculate_score(
        state["parsed_resume"], state["parsed_job"], state["skill_matches"], config
    )
    report = build_report(
        analysis_id=state["analysis_id"],
        created_at=state["created_at"],
        job_title=state.get("job_title"),
        resume=state["parsed_resume"],
        job=state["parsed_job"],
        summary=state["summary"],
        evaluation=state["evaluation"],
        skill_matches=state["skill_matches"],
        score=score,
        web=state.get("web_result"),
        web_requested=bool(state.get("enable_web_research")),
        warnings=state.get("warnings", []),
        completed_nodes=state.get("completed_nodes", []),
        llm_model=llm.model_name if llm else None,
        ai_nodes_used=state.get("ai_nodes_used", []),
        ai_fallbacks=state.get("ai_fallbacks", []),
    )

    # Saving: a storage problem must never destroy a finished analysis.
    if state.get("save_result", True):
        storage, notes = persist_report(
            get_repository(),
            report,
            job_title=state.get("job_title"),
            job_text=normalize_text(state["job_description"]),
            web_requested=bool(state.get("enable_web_research")),
            web_consented=bool(state.get("web_research_consent")),
        )
    else:
        storage = StorageSection(
            stored=False, note=state.get("storage_note") or "Saving was not requested."
        )
        notes = []

    report = report.model_copy(
        update={
            "storage": storage,
            "warnings": list(dict.fromkeys([*report.warnings, *notes])),
        }
    )
    return {"report": report}