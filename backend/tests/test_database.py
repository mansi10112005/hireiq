"""Database tests. Most need a running MongoDB and are SKIPPED if it is not available."""

import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.job_parser import parse_job_description
from app.services.repository import Repository
from app.workflows.graph import build_workflow

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
SAMPLE = (SAMPLES / "sample_resume.txt").read_bytes()
OTHER_PERSON = SAMPLE.replace(b"jane.example@example.com", b"other.person@example.com").replace(
    b"Jane Example", b"Other Person"
)


def run_workflow(resume_bytes: bytes, job_text: str = JOB_TEXT):
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
    return build_workflow().invoke(state)["report"]


def save(repo, report, job_text: str = JOB_TEXT):
    return repo.save_analysis(
        report,
        job_title="Backend Developer",
        job_text=job_text,
        web_requested=False,
        web_consented=False,
    )


@pytest.fixture()
def repo():
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=1500, tz_aware=True)
    try:
        client.admin.command("ping")
    except PyMongoError:
        client.close()
        pytest.skip("MongoDB is not running; start it to run the database tests.")
    db_name = f"hireiq_test_{uuid.uuid4().hex[:8]}"
    yield Repository(client[db_name], retention_days=0)
    client.drop_database(db_name)  # the temporary database is always removed
    client.close()


def unreachable_repository() -> Repository:
    client = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=300)
    return Repository(client["never_used"], retention_days=0)


# ---------- Needs MongoDB ----------
def test_report_round_trip(repo):
    report = run_workflow(SAMPLE)
    ids = save(repo, report)

    loaded = repo.get_analysis(ids.analysis_id)

    assert loaded.analysis_id == report.analysis_id
    assert loaded.score.value == report.score.value == 67
    assert loaded.candidate_name == "Jane Example"
    assert loaded.resume.contact.email == "jane.example@example.com"
    assert loaded.resume.contact.phone is None  # phone is deliberately not stored
    assert loaded.storage.stored is True
    assert [m.name for m in loaded.skill_matches.matches] == [
        m.name for m in report.skill_matches.matches
    ]


def test_only_necessary_personal_data_is_stored(repo):
    ids = save(repo, run_workflow(SAMPLE))

    analysis = repo._db["analyses"].find_one({"_id": ids.analysis_id})
    candidate = repo._db["candidates"].find_one({"_id": ids.candidate_id})

    assert "resume_text" not in analysis and "resume_text" not in analysis["report"]
    assert analysis["report"]["resume"]["contact"] == {
        "name": None, "email": None, "phone": None, "github_url": None, "linkedin_url": None,
    }
    assert "jane.example@example.com" not in json.dumps(analysis, default=str)
    assert set(candidate) <= {
        "_id", "name", "email", "email_hash", "first_seen_at", "last_analysis_at", "expires_at",
    }
    # External research is kept apart from resume facts
    assert "web_intelligence" not in analysis["report"]
    assert analysis["external_research"]["status"] == "not_requested"


def test_same_person_and_same_job_are_reused(repo):
    first = save(repo, run_workflow(SAMPLE))
    second = save(repo, run_workflow(SAMPLE))

    assert first.candidate_id == second.candidate_id
    assert first.job_id == second.job_id
    candidates, total = repo.list_candidates(limit=10, skip=0)
    assert total == 1
    assert candidates[0].analysis_count == 2


def test_identical_job_text_is_reused(repo):
    parsed = parse_job_description(JOB_TEXT)

    first, created_first = repo.create_job("Backend Developer", JOB_TEXT, parsed)
    second, created_second = repo.create_job("Backend Developer", JOB_TEXT + "\n\n", parsed)
    third, created_third = repo.create_job("Backend Developer", JOB_TEXT + "\nAlso Rust.", parsed)

    assert created_first is True and created_second is False
    assert first.id == second.id  # a whitespace-only difference is still the same job
    assert created_third is True and third.id != first.id
    assert "Python" in {s.name for s in first.parsed.required_skills}
    assert first.description.startswith("Backend Developer (Python)")  # original text kept


def test_history_pagination_and_filters(repo):
    other_job = "Requirements\n- Strong Python and SQL skills.\n- Experience with Git."
    a1 = save(repo, run_workflow(SAMPLE))
    a2 = save(repo, run_workflow(SAMPLE))
    b1 = save(repo, run_workflow(OTHER_PERSON, other_job), job_text=other_job)

    page, total = repo.list_analyses(limit=2, skip=0)
    assert total == 3 and len(page) == 2
    assert page[0].id == b1.analysis_id  # newest first
    assert page[0].candidate_name == "Other Person"
    assert page[0].score is not None

    assert repo.list_analyses(job_id=a1.job_id)[1] == 2
    assert repo.list_analyses(candidate_id=b1.candidate_id)[1] == 1
    assert repo.list_analyses(limit=2, skip=2)[0][0].id == a1.analysis_id
    assert a1.candidate_id == a2.candidate_id != b1.candidate_id


def test_deleting_the_last_analysis_removes_the_candidate(repo):
    ids = save(repo, run_workflow(SAMPLE))

    repo.delete_analysis(ids.analysis_id)

    assert repo.list_candidates(limit=10, skip=0)[1] == 0
    with pytest.raises(AppError) as error:
        repo.get_analysis(ids.analysis_id)
    assert error.value.status_code == 404


def test_deleting_a_candidate_removes_all_their_analyses(repo):
    first = save(repo, run_workflow(SAMPLE))
    save(repo, run_workflow(SAMPLE))
    other = save(repo, run_workflow(OTHER_PERSON))

    repo.delete_candidate(first.candidate_id)

    remaining, total = repo.list_analyses()
    assert total == 1 and remaining[0].candidate_id == other.candidate_id
    with pytest.raises(AppError):
        repo.get_candidate(first.candidate_id)


def test_a_job_with_analyses_needs_cascade_to_be_deleted(repo):
    ids = save(repo, run_workflow(SAMPLE))

    with pytest.raises(AppError) as error:
        repo.delete_job(ids.job_id, cascade=False)
    assert error.value.status_code == 409 and error.value.code == "job_in_use"

    repo.delete_job(ids.job_id, cascade=True)

    assert repo.list_jobs(limit=10, skip=0)[1] == 0
    assert repo.list_analyses()[1] == 0
    assert repo.list_candidates(limit=10, skip=0)[1] == 0


def test_retention_sets_an_expiry_date(repo):
    with_retention = Repository(repo._db, retention_days=30)
    ids = save(with_retention, run_workflow(SAMPLE))

    analysis = repo._db["analyses"].find_one({"_id": ids.analysis_id})
    candidate = repo._db["candidates"].find_one({"_id": ids.candidate_id})

    assert abs((analysis["expires_at"] - analysis["created_at"]) - timedelta(days=30)) < timedelta(minutes=5)
    assert "expires_at" in candidate


def test_workflow_saves_the_report(repo, monkeypatch):
    monkeypatch.setattr("app.workflows.nodes.get_repository", lambda: repo)

    report = run_workflow(SAMPLE)

    assert report.storage.stored is True
    assert repo.get_analysis(report.analysis_id).score.value == 67


# ---------- Needs no MongoDB ----------
def test_unreachable_database_gives_a_clear_error():
    with pytest.raises(AppError) as error:
        unreachable_repository().list_jobs(limit=10, skip=0)

    assert error.value.status_code == 503
    assert error.value.code == "database_unavailable"
    assert "mongodb://" not in error.value.message  # never leak connection details


def test_database_failure_does_not_destroy_the_analysis(monkeypatch):
    monkeypatch.setattr("app.workflows.nodes.get_repository", unreachable_repository)

    report = run_workflow(SAMPLE)

    assert report.score.value == 67  # the analysis itself still worked
    assert report.storage.stored is False
    assert any("not reachable" in warning for warning in report.warnings)