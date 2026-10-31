"""Tests for the analysis workflow. No server needed: we call the graph and nodes directly."""

from pathlib import Path

import pytest

from app.core.errors import AppError
from app.workflows.graph import build_workflow
from app.workflows.nodes import WorkflowStateError, cv_parsing_node

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")

PIPELINE_WITHOUT_WEB = [
    "resume_upload",
    "text_extraction",
    "cv_parsing",
    "jd_skill_extraction",
    "candidate_summary",
    "ai_evaluation",
    "skills_matching",
    "score_and_store",
]


def make_state(filename: str = "sample_resume.txt", **overrides) -> dict:
    state = {
        "filename": filename,
        "file_bytes": (SAMPLES / filename).read_bytes(),
        "job_title": "Backend Developer",
        "job_description": JOB_TEXT,
        "enable_web_research": False,
        "web_research_consent": False,
        "warnings": [],
        "completed_nodes": [],
    }
    state.update(overrides)
    return state


def test_full_workflow_without_web_research():
    report = build_workflow().invoke(make_state())["report"]

    assert report.pipeline == PIPELINE_WITHOUT_WEB
    assert report.candidate_name == "Jane Example"
    assert report.score.value is None  # scoring is not implemented yet
    assert report.storage.stored is False
    assert report.web_intelligence.status == "not_requested"

    statuses = {m.name: m.status for m in report.skill_matches.matches}
    assert statuses["Python"] == "supported"
    assert statuses["PostgreSQL"] == "supported"
    assert statuses["SQL"] == "partial"  # listed in Skills only
    assert statuses["Kubernetes"] == "unverified"
    assert report.unverified_required_skills == []

    assert report.evaluation.experience_checks[0].status == "unverified"
    assert any("SQL" in question for question in report.interview_questions)


def test_web_research_runs_only_with_consent():
    state = make_state(enable_web_research=True, web_research_consent=True)
    report = build_workflow().invoke(state)["report"]

    assert report.web_intelligence.status == "mock"
    assert report.pipeline.index("web_intelligence") < report.pipeline.index("score_and_store")


def test_web_research_is_skipped_without_consent():
    state = make_state(enable_web_research=True, web_research_consent=False)
    report = build_workflow().invoke(state)["report"]

    assert report.web_intelligence.status == "skipped_no_consent"
    assert "web_intelligence" not in report.pipeline
    assert any("consent" in warning for warning in report.warnings)


def test_invalid_file_stops_the_workflow():
    with pytest.raises(AppError) as error:
        build_workflow().invoke(make_state("fake.pdf"))
    assert error.value.code == "file_content_mismatch"


def test_scanned_pdf_reports_ocr_required():
    with pytest.raises(AppError) as error:
        build_workflow().invoke(make_state("blank_scan_like.pdf"))
    assert error.value.code == "ocr_required"


def test_a_node_can_be_tested_on_its_own():
    text = "Jane Example\nSKILLS\nPython, SQL, Git and Docker are listed here for this test."
    update = cv_parsing_node({"resume_text": text})

    names = {skill.name for skill in update["parsed_resume"].skills}
    assert {"Python", "SQL", "Git", "Docker"} <= names
    assert update["completed_nodes"] == ["cv_parsing"]


def test_node_without_required_state_fails_clearly():
    with pytest.raises(WorkflowStateError):
        cv_parsing_node({})