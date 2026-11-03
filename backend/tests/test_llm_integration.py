"""Tests for the AI integration. They use FAKE AI clients, so no network or API key is needed."""

import types
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.services.evidence_check import SourceText
from app.services.job_parser import parse_job_description
from app.services.llm_client import GroqStructuredLLM, LLMUnavailableError
from app.services.resume_parser import parse_resume
from app.workflows.graph import build_workflow
from app.workflows.nodes import (
    ai_evaluation_node,
    candidate_summary_node,
    cv_parsing_node,
    jd_skill_extraction_node,
)

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
RESUME_TEXT = (SAMPLES / "sample_resume.txt").read_text(encoding="utf-8")


class FakeLLM:
    """Pretends to be the AI. `responses` maps schema_name -> reply dict (or an Exception)."""

    model_name = "fake-model"

    def __init__(self, responses: dict):
        self.responses = responses

    def generate(self, *, system, user, output_model, schema_name, max_output_tokens=1500):
        reply = self.responses[schema_name]
        if isinstance(reply, Exception):
            raise reply
        return output_model.model_validate(reply)  # same validation the real client does


def use_fake(monkeypatch, fake):
    monkeypatch.setattr("app.workflows.nodes.get_llm_client", lambda: fake)


def empty_resume_extraction(**changes):
    data = {
        "name": None, "email": None, "phone": None, "summary": None,
        "education": [], "experience": [], "projects": [], "skills": [],
        "certifications": [], "stated_years_of_experience": None, "stated_years_quote": None,
    }
    data.update(changes)
    return data


# ---------- Evidence checker ----------
def test_evidence_checker_accepts_real_quotes_and_rejects_invented_ones():
    source = SourceText("Built REST APIs using FastAPI\nand PostgreSQL for an internal tool.")
    assert source.contains("built REST apis using fastapi and postgresql")
    assert not source.contains("Deployed everything on Kubernetes clusters")
    assert not source.contains("")
    assert not source.contains("ab")


# ---------- The Groq wrapper (with a stub client, no network) ----------
class Ping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    language: str


class _Completions:
    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = 0
        self.last_kwargs = {}

    def create(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        content = self.contents.pop(0)
        message = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)], usage=None)


def make_wrapper(contents):
    completions = _Completions(contents)
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))
    return GroqStructuredLLM(get_settings(), client=client), completions


def test_wrapper_retries_once_after_a_malformed_reply():
    llm, completions = make_wrapper(["this is not json", '{"answer": "Paris", "language": "English"}'])
    result = llm.generate(
        system="s", user="u", output_model=Ping, schema_name="ping", max_output_tokens=100
    )
    assert result.answer == "Paris"
    assert completions.calls == 2
    assert completions.last_kwargs["response_format"]["json_schema"]["name"] == "ping"


def test_wrapper_gives_up_after_two_unusable_replies():
    llm, completions = make_wrapper(["not json", '{"wrong": 1}'])
    with pytest.raises(LLMUnavailableError):
        llm.generate(system="s", user="u", output_model=Ping, schema_name="ping")
    assert completions.calls == 2


# ---------- AI results are verified against the text ----------
def test_ai_resume_extraction_keeps_only_verified_skills(monkeypatch):
    text = RESUME_TEXT + "\nTools: Figma, Canva"
    fake = FakeLLM(
        {
            "resume_extraction": empty_resume_extraction(
                skills=[
                    {"name": "Figma", "evidence_quote": "Tools: Figma, Canva"},
                    {"name": "Canva", "evidence_quote": "Tools: Figma, Canva"},
                    {"name": "Kubernetes", "evidence_quote": "Deployed everything on Kubernetes clusters"},
                    {"name": "Quantum computing", "evidence_quote": "Python script that scores resumes against keywords"},
                ]
            )
        }
    )
    use_fake(monkeypatch, fake)

    update = cv_parsing_node({"resume_text": text})
    skills = {s.name: s for s in update["parsed_resume"].skills}

    assert {"Figma", "Canva"} <= set(skills)
    assert "Kubernetes" not in skills  # invented quote
    assert "Quantum computing" not in skills  # real quote, but the skill is not in the text
    assert "Figma" in skills["Figma"].evidence[0].snippet
    assert update["ai_nodes_used"] == ["cv_parsing"]
    assert any("2 AI-extracted" in warning for warning in update["warnings"])


def test_ai_job_extraction_verifies_and_can_upgrade_importance(monkeypatch):
    fake = FakeLLM(
        {
            "job_extraction": {
                "skills": [
                    {"name": "FastAPI", "importance": "required", "evidence_quote": "Design and build REST APIs using FastAPI."},
                    {"name": "API contracts", "importance": "unspecified", "evidence_quote": "Collaborate with the frontend team on API contracts."},
                    {"name": "Rust", "importance": "required", "evidence_quote": "Rust experience is required"},
                ],
                "responsibilities": [],
                "experience_requirements": [],
            }
        }
    )
    use_fake(monkeypatch, fake)

    update = jd_skill_extraction_node({"job_description": JOB_TEXT, "job_title": "Backend Developer"})
    job = update["parsed_job"]

    assert "FastAPI" in {s.name for s in job.required_skills}  # upgraded from "unspecified"
    assert "API contracts" in {s.name for s in job.other_mentioned_skills}  # new, verified
    every_skill = {s.name for s in (*job.required_skills, *job.preferred_skills, *job.other_mentioned_skills)}
    assert "Rust" not in every_skill  # invented


def test_ai_summary_drops_statements_without_a_real_quote(monkeypatch):
    fake = FakeLLM(
        {
            "candidate_summary": {
                "professional_summary": {
                    "text": "Third-year IT student focused on backend development.",
                    "evidence_quote": "Third-year IT student interested in backend development",
                },
                "key_strengths": [
                    {"text": "Built REST APIs with FastAPI during an internship.", "evidence_quote": "Built REST APIs using FastAPI and PostgreSQL"},
                    {"text": "Led a team of ten engineers.", "evidence_quote": "Led a team of ten engineers"},
                ],
                "experience_highlights": [],
                "project_highlights": [],
            }
        }
    )
    use_fake(monkeypatch, fake)

    update = candidate_summary_node(
        {"parsed_resume": parse_resume(RESUME_TEXT), "resume_text": RESUME_TEXT}
    )
    summary = update["summary"]

    assert summary.professional_summary.origin == "ai"
    assert [s.origin for s in summary.key_strengths] == ["ai"]  # the invented one was dropped
    assert "FastAPI" in summary.key_strengths[0].text
    assert summary.generator == "ai:fake-model"
    assert any("1 AI-written" in warning for warning in update["warnings"])


def test_ai_evaluation_drops_entries_it_cannot_verify(monkeypatch):
    fake = FakeLLM(
        {
            "candidate_evaluation": {
                "relevant_entries": [
                    {
                        "section": "experience",
                        "heading": "Backend Intern, Sample Software Pvt Ltd, May 2025 - Jul 2025",
                        "matched_skills": ["FastAPI", "PostgreSQL"],
                        "why_relevant": "Built APIs with the same stack the role uses.",
                        "evidence_quote": "Built REST APIs using FastAPI and PostgreSQL",
                    },
                    {
                        "section": "projects",
                        "heading": "Invented Project",
                        "matched_skills": ["Python"],
                        "why_relevant": "Not real.",
                        "evidence_quote": "Invented quote that is not in the resume",
                    },
                ],
                "notes": ["Strong overlap with the role's backend stack."],
            }
        }
    )
    use_fake(monkeypatch, fake)

    update = ai_evaluation_node(
        {
            "parsed_resume": parse_resume(RESUME_TEXT),
            "parsed_job": parse_job_description(JOB_TEXT),
            "resume_text": RESUME_TEXT,
        }
    )
    evaluation = update["evaluation"]

    assert len(evaluation.relevant_entries) == 1
    assert evaluation.relevant_entries[0].explanation.startswith("Built APIs")
    assert evaluation.evaluator == "ai:fake-model"
    assert len(evaluation.experience_checks) == 1  # still deterministic code, not AI


# ---------- Failure handling ----------
def make_state(filename: str = "sample_resume.txt") -> dict:
    return {
        "filename": filename,
        "file_bytes": (SAMPLES / filename).read_bytes(),
        "job_title": "Backend Developer",
        "job_description": JOB_TEXT,
        "enable_web_research": False,
        "web_research_consent": False,
        "warnings": [],
        "completed_nodes": [],
    }


def test_provider_failure_falls_back_to_rule_based_results(monkeypatch):
    failing = LLMUnavailableError("the AI provider's rate limit was reached; try again in a minute")
    fake = FakeLLM(
        {
            "resume_extraction": failing,
            "job_extraction": failing,
            "candidate_summary": failing,
            "candidate_evaluation": failing,
        }
    )
    use_fake(monkeypatch, fake)

    report = build_workflow().invoke(make_state())["report"]

    assert report.candidate_name == "Jane Example"  # the rule-based result still works
    assert "Python" in {s.name for s in report.resume.skills}
    assert report.ai_usage.nodes_using_ai == []
    assert report.ai_usage.nodes_with_fallback == [
        "cv_parsing",
        "jd_skill_extraction",
        "candidate_summary",
        "ai_evaluation",
    ]
    assert any("rate limit" in warning for warning in report.warnings)


def test_prompt_injection_text_is_flagged_and_does_not_change_the_result():
    report = build_workflow().invoke(make_state("injection_resume.txt"))["report"]

    assert any("instructions to an AI" in warning for warning in report.warnings)
    assert report.score.value is None