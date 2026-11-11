"""Checks that the evidence behind each skill match really exists in the source text."""

from app.schemas.analysis import EvidenceValidation, SkillMatchResult
from app.services.evidence_check import SourceText


def validate_match_evidence(
    result: SkillMatchResult, resume_text: str, job_text: str
) -> tuple[SkillMatchResult, list[str]]:
    """Drop evidence that cannot be found in the text, and downgrade matches that depended on it."""
    resume_source = SourceText(resume_text)
    job_source = SourceText(job_text)
    checked = 0
    rejected = 0
    validated = []

    for match in result.matches:
        resume_evidence = []
        for item in match.evidence:
            checked += 1
            if resume_source.contains(item.snippet):
                resume_evidence.append(item)
            else:
                rejected += 1

        job_evidence = []
        for item in match.requirement_evidence:
            checked += 1
            if job_source.contains(item.snippet):
                job_evidence.append(item)
            else:
                rejected += 1

        status, note = match.status, match.note
        shown_in_use = [e for e in resume_evidence if e.section != "skills"]
        if match.status in ("supported", "partial") and not resume_evidence:
            status = "unverified"
            note = (
                "The evidence for this skill could not be verified in the resume text, "
                "so it was not counted."
            )
        elif match.status == "supported" and not shown_in_use:
            status = "partial"
            note = "Only Skills-section evidence could be verified, so credit was reduced to partial."

        validated.append(
            match.model_copy(
                update={
                    "status": status,
                    "note": note,
                    "evidence": resume_evidence,
                    "requirement_evidence": job_evidence,
                }
            )
        )

    notes: list[str] = []
    if rejected:
        notes.append(
            f"{rejected} pieces of evidence could not be verified in the source text and were "
            "not counted."
        )
    return (
        SkillMatchResult(
            method="evidence_checked_v1",
            matches=validated,
            validation=EvidenceValidation(checked=checked, rejected=rejected),
        ),
        notes,
    )