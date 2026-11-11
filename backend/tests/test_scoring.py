"""Tests for the deterministic scoring. They need no network, no AI and no API key."""

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.analysis import SkillMatch, SkillMatchResult
from app.schemas.evidence import Evidence
from app.services.evidence_validation import validate_match_evidence
from app.services.scoring_config import build_scoring_config
from app.workflows.graph import build_workflow

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
SAMPLE_RESUME = (SAMPLES / "sample_resume.txt").read_bytes()

WEAK_RESUME = (
    "Alex Doe\nSKILLS\nPython\nEXPERIENCE\nBackend Intern, Example Co, 2024 - 2025\n"
    "- Wrote small scripts in Python for data cleanup."
).encode()

UNRELATED_RESUME = (
    "Alex Doe\nI enjoy hiking, painting and cooking, and reading books every week."
).encode()


def analyze(resume_bytes: bytes, job_text: str = JOB_TEXT, config=None):
    state = {
        "filename": "candidate.txt",
        "file_bytes": resume_bytes,
        "job_title": "Backend Developer",
        "job_description": job_text,
        "enable_web_research": False,
        "web_research_consent": False,
        "warnings": [],
        "completed_nodes": [],
    }
    if config is not None:
        state["scoring_config"] = config
    return build_workflow().invoke(state)["report"]


def component(report, key):
    return next(c for c in report.score.components if c.key == key)


def test_sample_candidate_score_and_breakdown():
    report = analyze(SAMPLE_RESUME)
    score = report.score

    assert score.status == "calculated"
    assert score.value == 67
    assert score.evidence_level == "moderate"
    assert component(report, "required_skills").fraction == pytest.approx(0.8)
    assert component(report, "preferred_skills").fraction == pytest.approx(0.125)
    assert component(report, "experience").fraction == pytest.approx(0.5)
    assert component(report, "projects_qualifications").fraction == pytest.approx(1.0)
    assert sum(c.points for c in score.components) == pytest.approx(score.exact, abs=0.05)
    assert sum(c.effective_weight for c in score.components) == pytest.approx(100, abs=0.1)


def test_weights_are_configurable_and_normalized():
    only_required = build_scoring_config(
        get_settings(),
        {"required_skills": 100, "preferred_skills": 0, "experience": 0, "projects_qualifications": 0},
    )
    assert analyze(SAMPLE_RESUME, config=only_required).score.value == 80  # 0.8 x 100

    relative = build_scoring_config(
        get_settings(),
        {"required_skills": 20, "preferred_skills": 10, "experience": 10, "projects_qualifications": 0},
    )
    report = analyze(SAMPLE_RESUME, config=relative)
    assert report.score.weights.required_skills == pytest.approx(50)
    assert report.score.weights.preferred_skills == pytest.approx(25)
    assert report.score.weights.experience == pytest.approx(25)
    assert report.score.value == 56  # 0.8x50 + 0.125x25 + 0.5x25 = 55.625


def test_weights_of_components_without_data_are_redistributed():
    job_without_preferred = (
        "Requirements\n- Strong Python and SQL skills.\n"
        "- 2+ years of experience in backend development."
    )
    report = analyze(SAMPLE_RESUME, job_text=job_without_preferred)

    preferred = component(report, "preferred_skills")
    assert preferred.applicable is False
    assert preferred.effective_weight == 0
    assert sum(c.effective_weight for c in report.score.components) == pytest.approx(100, abs=0.1)
    assert report.score.value == 62  # 0.75x58.8 + 0x23.5 + 1.0x17.6 = 61.76
    assert any("shared proportionally" in note for note in report.score.notes)


def test_score_is_never_below_one():
    report = analyze(UNRELATED_RESUME)

    assert report.score.status == "calculated"
    assert report.score.value == 1
    assert report.score.evidence_level == "limited"


def test_score_not_calculated_without_recognised_requirements():
    vague_job = "We are looking for a friendly person who enjoys working with teams and customers."
    report = analyze(SAMPLE_RESUME, job_text=vague_job)

    assert report.score.status == "not_calculated"
    assert report.score.value is None
    assert all(not c.applicable for c in report.score.components)


def test_scoring_is_consistent_across_candidates():
    strong = analyze(SAMPLE_RESUME)
    weak = analyze(WEAK_RESUME)

    assert weak.score.value == 20  # 0.2x50 + 0x15 + 0.5x20 + 0x15
    assert weak.score.value < strong.score.value
    assert strong.score.weights == weak.score.weights  # same criteria for everyone
    assert strong.score.method == weak.score.method
    assert analyze(SAMPLE_RESUME).score.value == strong.score.value  # deterministic


def test_prompt_injection_does_not_change_the_score():
    injected = analyze((SAMPLES / "injection_resume.txt").read_bytes())
    assert injected.score.value == analyze(SAMPLE_RESUME).score.value == 67


def test_fabricated_evidence_is_not_counted():
    fabricated = SkillMatchResult(
        matches=[
            SkillMatch(
                name="Kubernetes",
                importance="required",
                status="supported",
                evidence=[
                    Evidence(
                        source="resume",
                        section="experience",
                        snippet="Managed Kubernetes clusters in production",
                    )
                ],
                note="x",
            )
        ]
    )
    resume_text = SAMPLE_RESUME.decode()

    validated, notes = validate_match_evidence(fabricated, resume_text, JOB_TEXT)

    assert validated.matches[0].status == "unverified"
    assert validated.matches[0].evidence == []
    assert validated.validation.rejected == 1
    assert any("could not be verified" in note for note in notes)


def test_all_zero_weights_are_rejected():
    with pytest.raises(AppError) as error:
        build_scoring_config(
            get_settings(),
            {"required_skills": 0, "preferred_skills": 0, "experience": 0, "projects_qualifications": 0},
        )
    assert error.value.code == "invalid_scoring_weights"