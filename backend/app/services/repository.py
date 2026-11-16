"""All database operations live here, so the rest of the app never touches MongoDB directly."""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from pymongo import DESCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.database import database_errors, get_database
from app.core.errors import AppError
from app.models.documents import (
    build_analysis_doc,
    build_job_doc,
    compute_job_hash,
    doc_to_report,
    new_id,
    sha256_hex,
)
from app.schemas.analysis import AnalysisReport
from app.schemas.job import ParsedJobDescription
from app.schemas.records import (
    AnalysisSummary,
    CandidateRecord,
    CandidateSummary,
    JobRecord,
    JobSummary,
)
from app.schemas.resume import ContactInfo

logger = logging.getLogger("hireiq")


@dataclass
class SavedIds:
    analysis_id: str
    candidate_id: str
    job_id: str


def _not_found(kind: str) -> AppError:
    return AppError(f"{kind} not found.", status_code=404, code="not_found")


class Repository:
    def __init__(self, db: Database, retention_days: int = 0) -> None:
        self._db = db
        self._jobs = db["jobs"]
        self._candidates = db["candidates"]
        self._analyses = db["analyses"]
        self._retention_days = retention_days
        self._indexes_ready = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ setup
    def ping(self) -> None:
        with database_errors():
            self._db.client.admin.command("ping")

    def ensure_indexes(self) -> None:
        """Create indexes once. Creating an index that already exists does nothing."""
        if self._indexes_ready:
            return
        with self._lock:
            if self._indexes_ready:
                return
            with database_errors():
                self._jobs.create_index("content_hash", unique=True)
                self._jobs.create_index([("created_at", DESCENDING)])
                # Unique only for candidates that HAVE an email hash
                self._candidates.create_index(
                    "email_hash",
                    unique=True,
                    partialFilterExpression={"email_hash": {"$type": "string"}},
                )
                self._candidates.create_index([("last_analysis_at", DESCENDING)])
                self._analyses.create_index([("created_at", DESCENDING)])
                self._analyses.create_index("job_id")
                self._analyses.create_index("candidate_id")
                # TTL indexes: MongoDB deletes a document once its expires_at date has passed
                self._candidates.create_index("expires_at", expireAfterSeconds=0)
                self._analyses.create_index("expires_at", expireAfterSeconds=0)
            self._indexes_ready = True

    # ------------------------------------------------------------------ helpers
    def _expiry(self, now: datetime) -> datetime | None:
        if self._retention_days > 0:
            return now + timedelta(days=self._retention_days)
        return None

    def _count_by(self, field: str, ids: list[str]) -> dict[str, int]:
        """How many analyses reference each id (one query for the whole list)."""
        if not ids:
            return {}
        rows = self._analyses.aggregate(
            [
                {"$match": {field: {"$in": ids}}},
                {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
            ]
        )
        return {row["_id"]: row["n"] for row in rows}

    @staticmethod
    def _job_summary(doc: dict, analysis_count: int) -> JobSummary:
        parsed = doc["parsed"]
        return JobSummary(
            id=doc["_id"],
            title=doc.get("title"),
            created_at=doc["created_at"],
            required_skill_count=len(parsed.get("required_skills", [])),
            preferred_skill_count=len(parsed.get("preferred_skills", [])),
            analysis_count=analysis_count,
        )

    def _job_record(self, doc: dict, analysis_count: int) -> JobRecord:
        summary = self._job_summary(doc, analysis_count)
        return JobRecord(
            **summary.model_dump(),
            description=doc["description"],
            parsed=ParsedJobDescription.model_validate(doc["parsed"]),
        )

    def _analysis_summaries(
        self, query: dict, limit: int, skip: int
    ) -> tuple[list[AnalysisSummary], int]:
        total = self._analyses.count_documents(query)
        docs = list(
            self._analyses.find(query, projection={"report": 0, "external_research": 0})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        candidate_ids = list({d["candidate_id"] for d in docs})
        job_ids = list({d["job_id"] for d in docs})
        candidates = {
            c["_id"]: c
            for c in self._candidates.find({"_id": {"$in": candidate_ids}}, projection={"name": 1})
        }
        jobs = {
            j["_id"]: j for j in self._jobs.find({"_id": {"$in": job_ids}}, projection={"title": 1})
        }
        items = [
            AnalysisSummary(
                id=d["_id"],
                created_at=d["created_at"],
                candidate_id=d["candidate_id"],
                candidate_name=candidates.get(d["candidate_id"], {}).get("name"),
                job_id=d["job_id"],
                job_title=jobs.get(d["job_id"], {}).get("title"),
                score=d.get("score_value"),
                evidence_level=d.get("evidence_level"),
                ai_used=d.get("ai_used", False),
            )
            for d in docs
        ]
        return items, total

    # ------------------------------------------------------------------ jobs
    def find_job_by_text(self, title: str | None, text: str) -> JobRecord | None:
        with database_errors():
            doc = self._jobs.find_one({"content_hash": compute_job_hash(title, text)})
            if doc is None:
                return None
            return self._job_record(doc, self._analyses.count_documents({"job_id": doc["_id"]}))

    def create_job(
        self, title: str | None, text: str, parsed: ParsedJobDescription
    ) -> tuple[JobRecord, bool]:
        """Save a job, or return the existing one with identical text. Returns (job, created)."""
        with database_errors():
            self.ensure_indexes()
            job_hash = compute_job_hash(title, text)
            existing = self._jobs.find_one({"content_hash": job_hash})
            if existing is not None:
                count = self._analyses.count_documents({"job_id": existing["_id"]})
                return self._job_record(existing, count), False

            doc = build_job_doc(title, text, parsed)
            try:
                self._jobs.insert_one(doc)
            except DuplicateKeyError:  # another request created it a moment ago
                existing = self._jobs.find_one({"content_hash": job_hash})
                count = self._analyses.count_documents({"job_id": existing["_id"]})
                return self._job_record(existing, count), False
            return self._job_record(doc, 0), True

    def get_job(self, job_id: str) -> JobRecord:
        with database_errors():
            doc = self._jobs.find_one({"_id": job_id})
            if doc is None:
                raise _not_found("Job")
            count = self._analyses.count_documents({"job_id": job_id})
            return self._job_record(doc, count)

    def list_jobs(self, limit: int, skip: int) -> tuple[list[JobSummary], int]:
        with database_errors():
            total = self._jobs.count_documents({})
            docs = list(
                self._jobs.find({}, projection={"description": 0})
                .sort("created_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            counts = self._count_by("job_id", [d["_id"] for d in docs])
        return [self._job_summary(d, counts.get(d["_id"], 0)) for d in docs], total

    def delete_job(self, job_id: str, cascade: bool = False) -> None:
        with database_errors():
            if self._jobs.count_documents({"_id": job_id}, limit=1) == 0:
                raise _not_found("Job")
            in_use = self._analyses.count_documents({"job_id": job_id})
            if in_use and not cascade:
                raise AppError(
                    f"This job has {in_use} saved analyses. Delete them first, or repeat the "
                    "request with cascade=true to delete them too.",
                    status_code=409,
                    code="job_in_use",
                )
            if in_use:
                candidate_ids = self._analyses.distinct("candidate_id", {"job_id": job_id})
                self._analyses.delete_many({"job_id": job_id})  # analyses first (personal data)
                for candidate_id in candidate_ids:
                    self._delete_candidate_if_orphaned(candidate_id)
            self._jobs.delete_one({"_id": job_id})

    # ------------------------------------------------------------------ candidates
    def _upsert_candidate(
        self, contact: ContactInfo, now: datetime, expires_at: datetime | None
    ) -> str:
        email = (contact.email or "").strip()
        if email:
            email_hash = sha256_hex(email.lower())
            set_fields: dict = {"last_analysis_at": now, "email": email}
            if contact.name:
                set_fields["name"] = contact.name
            if expires_at is not None:
                set_fields["expires_at"] = expires_at
            for _ in range(2):  # a second try covers a rare simultaneous insert
                try:
                    doc = self._candidates.find_one_and_update(
                        {"email_hash": email_hash},
                        {"$set": set_fields, "$setOnInsert": {"_id": new_id(), "first_seen_at": now}},
                        upsert=True,
                        return_document=ReturnDocument.AFTER,
                    )
                    return doc["_id"]
                except DuplicateKeyError:
                    continue
            raise RuntimeError("could not create the candidate record")

        # No email: we cannot recognise the person, so each analysis gets its own record.
        doc = {
            "_id": new_id(),
            "name": contact.name,
            "email": None,
            "first_seen_at": now,
            "last_analysis_at": now,
        }
        if expires_at is not None:
            doc["expires_at"] = expires_at
        self._candidates.insert_one(doc)
        return doc["_id"]

    def _delete_candidate_if_orphaned(self, candidate_id: str) -> None:
        if self._analyses.count_documents({"candidate_id": candidate_id}, limit=1) == 0:
            self._candidates.delete_one({"_id": candidate_id})

    def list_candidates(self, limit: int, skip: int) -> tuple[list[CandidateSummary], int]:
        with database_errors():
            total = self._candidates.count_documents({})
            docs = list(
                self._candidates.find({})
                .sort("last_analysis_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            counts = self._count_by("candidate_id", [d["_id"] for d in docs])
        items = [
            CandidateSummary(
                id=d["_id"],
                name=d.get("name"),
                email=d.get("email"),
                analysis_count=counts.get(d["_id"], 0),
                first_seen_at=d["first_seen_at"],
                last_analysis_at=d["last_analysis_at"],
            )
            for d in docs
        ]
        return items, total

    def get_candidate(self, candidate_id: str) -> CandidateRecord:
        with database_errors():
            doc = self._candidates.find_one({"_id": candidate_id})
            if doc is None:
                raise _not_found("Candidate")
            analyses, total = self._analysis_summaries({"candidate_id": candidate_id}, 100, 0)
        return CandidateRecord(
            id=doc["_id"],
            name=doc.get("name"),
            email=doc.get("email"),
            analysis_count=total,
            first_seen_at=doc["first_seen_at"],
            last_analysis_at=doc["last_analysis_at"],
            analyses=analyses,
        )

    def delete_candidate(self, candidate_id: str) -> None:
        """Right to erasure: removes the candidate AND every analysis about them."""
        with database_errors():
            if self._candidates.count_documents({"_id": candidate_id}, limit=1) == 0:
                raise _not_found("Candidate")
            self._analyses.delete_many({"candidate_id": candidate_id})  # analyses first
            self._candidates.delete_one({"_id": candidate_id})

    # ------------------------------------------------------------------ analyses
    def save_analysis(
        self,
        report: AnalysisReport,
        *,
        job_title: str | None,
        job_text: str,
        web_requested: bool,
        web_consented: bool,
    ) -> SavedIds:
        with database_errors():
            self.ensure_indexes()
            now = datetime.now(timezone.utc)
            expires_at = self._expiry(now)

            job, _created = self.create_job(job_title, job_text, report.job)
            candidate_id = self._upsert_candidate(report.resume.contact, now, expires_at)
            doc = build_analysis_doc(
                report,
                candidate_id=candidate_id,
                job_id=job.id,
                web_requested=web_requested,
                web_consented=web_consented,
                expires_at=expires_at,
            )
            self._analyses.insert_one(doc)
        return SavedIds(analysis_id=report.analysis_id, candidate_id=candidate_id, job_id=job.id)

    def list_analyses(
        self,
        *,
        job_id: str | None = None,
        candidate_id: str | None = None,
        limit: int = 20,
        skip: int = 0,
    ) -> tuple[list[AnalysisSummary], int]:
        query: dict = {}
        if job_id:
            query["job_id"] = job_id
        if candidate_id:
            query["candidate_id"] = candidate_id
        with database_errors():
            return self._analysis_summaries(query, limit, skip)

    def get_analysis(self, analysis_id: str) -> AnalysisReport:
        with database_errors():
            doc = self._analyses.find_one({"_id": analysis_id})
            if doc is None:
                raise _not_found("Analysis")
            candidate = self._candidates.find_one({"_id": doc["candidate_id"]})
        return doc_to_report(doc, candidate)

    def delete_analysis(self, analysis_id: str) -> None:
        with database_errors():
            doc = self._analyses.find_one_and_delete(
                {"_id": analysis_id}, projection={"candidate_id": 1}
            )
            if doc is None:
                raise _not_found("Analysis")
            self._delete_candidate_if_orphaned(doc["candidate_id"])


@lru_cache
def get_repository() -> Repository | None:
    """The shared repository, or None when storage is switched off."""
    settings = get_settings()
    if not settings.storage_enabled:
        return None
    return Repository(get_database(), settings.retention_days)