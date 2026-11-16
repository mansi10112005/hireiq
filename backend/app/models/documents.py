"""How our objects become MongoDB documents (and back). This is where privacy rules are enforced."""

import hashlib
import uuid
from datetime import datetime, timezone

from app.schemas.analysis import AnalysisReport
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ContactInfo
from app.services.text_extraction import normalize_text

SCHEMA_VERSION = 1


def new_id() -> str:
    return uuid.uuid4().hex


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_job_hash(title: str | None, text: str) -> str:
    """Same title + same text (ignoring whitespace differences) = same job."""
    return sha256_hex(f"{(title or '').strip()}\n{normalize_text(text)}")


def build_job_doc(title: str | None, text: str, parsed: ParsedJobDescription) -> dict:
    return {
        "_id": new_id(),
        "title": title,
        "description": normalize_text(text),
        "parsed": parsed.model_dump(mode="json"),
        "content_hash": compute_job_hash(title, text),
        "created_at": datetime.now(timezone.utc),
    }


def build_analysis_doc(
    report: AnalysisReport,
    *,
    candidate_id: str,
    job_id: str,
    web_requested: bool,
    web_consented: bool,
    expires_at: datetime | None,
) -> dict:
    """The stored analysis. Personal contact data is REMOVED (it lives only in `candidates`),
    and external research is kept in its own field, separate from resume facts."""
    data = report.model_dump(mode="json")
    external_research = data.pop("web_intelligence")
    data.pop("storage", None)  # derived when loading
    data["candidate_name"] = None
    data["resume"]["contact"] = ContactInfo().model_dump()  # all fields None

    doc = {
        "_id": report.analysis_id,
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "created_at": datetime.fromisoformat(report.created_at),
        "score_value": report.score.value,
        "evidence_level": report.score.evidence_level,
        "ai_used": bool(report.ai_usage.nodes_using_ai),
        "options": {
            "web_research_requested": web_requested,
            "web_research_consent_confirmed": web_consented,
        },
        "report": data,
        "external_research": external_research,
    }
    if expires_at is not None:
        doc["expires_at"] = expires_at
    return doc


def doc_to_report(doc: dict, candidate: dict | None) -> AnalysisReport:
    """Rebuild the full report from the stored pieces."""
    data = dict(doc["report"])
    data["web_intelligence"] = doc["external_research"]
    if candidate is not None:
        data["candidate_name"] = candidate.get("name")
        data["resume"]["contact"]["name"] = candidate.get("name")
        data["resume"]["contact"]["email"] = candidate.get("email")
    data["storage"] = {
        "stored": True,
        "candidate_id": doc["candidate_id"],
        "job_id": doc["job_id"],
        "note": "Loaded from the database. Phone number and links are not stored.",
    }
    return AnalysisReport.model_validate(data)