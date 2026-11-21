"""Comparison tests: one common yardstick, no ranking. No database or AI needed."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.schemas.records import JobRecord
from app.services.comparison import build_comparison
from app.services.job_parser import parse_job_description
from app.services.scoring_config import build_scoring_config, default_scoring_config
from app.workflows.graph import build_workflow

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
STRONG = (SAMPLES / "sample_resume.txt").read_bytes()
WEAK = (
    "Alex Doe\nSKILLS\nPython\nEXPERIENCE\nBackend Intern, Example Co, 2024 - 2025\n"
    "- Wrote small scripts in Python for data cleanup."
).encode()


def analyze(resume: bytes, config=None):
    state = {
        "filename": "candidate.txt",
        "file_bytes": resume,
        "job_title": "Backend Developer",
        "job_description": JOB_TEXT,
        "enable_web_research": False,
        "web_research_consent": False,
        "warnings": [],
        "completed_nodes": [],
    }
    if config is not None:
        state["scoring_config"] = config
    return build_workflow().invoke(state)["report"]


def make_job() -> JobRecord:
    parsed = parse_job_description(JOB_TEXT, "Backend Developer")
    return JobRecord(
        id="job-1",
        title="Backend Developer",
        created_at=datetime.now(timezone.utc),
        required_skill_count=len(parsed.required_skills),
        preferred_skill_count=len(parsed.preferred_skills),
        analysis_count=0,
        description=JOB_TEXT,
        parsed=parsed,
    )


def test_everyone_is_scored_by_the_same_criteria_and_not_ranked():
    strong, weak = analyze(STRONG), analyze(WEAK)
    config = default_scoring_config(get_settings())

    result = build_comparison(make_job(), [weak, strong], config)  # weak selected FIRST

    assert [c.candidate_name for c in result.candidates] == ["Alex Doe", "Jane Example"]  # order kept
    assert [c.score for c in result.candidates] == [20, 67]
    assert all(not c.score_changed for c in result.candidates)  # same as their own reports
    assert not hasattr(result.candidates[0], "rank")
    assert "not ranked" in result.disclaimer


def test_a_common_weighting_is_applied_to_everyone():
    only_required = build_scoring_config(
        get_settings(),
        {"required_skills": 100, "preferred_skills": 0, "experience": 0, "projects_qualifications": 0},
    )

    result = build_comparison(make_job(), [analyze(STRONG), analyze(WEAK)], only_required)

    assert [c.score for c in result.candidates] == [80, 20]  # 0.8 x 100 and 0.2 x 100
    assert result.scoring.weights.required_skills == pytest.approx(100)


def test_skill_rows_line_up_with_the_selected_candidates():
    result = build_comparison(
        make_job(), [analyze(STRONG), analyze(WEAK)], default_scoring_config(get_settings())
    )
    rows = {row.name: row.statuses for row in result.skills}

    assert rows["Python"] == ["supported", "supported"]
    assert rows["SQL"] == ["partial", "unverified"]  # listed only vs no evidence
    assert rows["Kubernetes"] == ["unverified", "unverified"]
    assert all(len(statuses) == 2 for statuses in rows.values())


def test_a_changed_score_is_flagged_not_hidden():
    # This report was ORIGINALLY scored with custom weights (80), the comparison uses the defaults (67).
    custom = build_scoring_config(
        get_settings(),
        {"required_skills": 100, "preferred_skills": 0, "experience": 0, "projects_qualifications": 0},
    )
    original = analyze(STRONG, config=custom)
    assert original.score.value == 80

    result = build_comparison(make_job(), [original], default_scoring_config(get_settings()))
    candidate = result.candidates[0]

    assert (candidate.stored_score, candidate.score) == (80, 67)
    assert candidate.score_changed is True
    assert any("differs from the original report" in note for note in result.notes)