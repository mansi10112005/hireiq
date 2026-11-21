"""Side-by-side comparison. Everyone is judged by the SAME job requirements and the SAME weights."""

from app.schemas.analysis import AnalysisReport
from app.schemas.comparison import (
    ComparedCandidate,
    ComparisonResult,
    ComparisonScoring,
    SkillComparisonRow,
)
from app.schemas.records import JobRecord
from app.schemas.scoring import ScoringConfig
from app.services.scoring import calculate_score
from app.services.scoring_config import SCORING_METHOD, normalize_weights
from app.services.skill_matcher import match_skills

DISCLAIMER = (
    "This comparison is a screening aid. Candidates are listed in the order you selected, not "
    "ranked, and HireIQ never rejects or shortlists anyone automatically. A missing skill means "
    "'no evidence found', not 'the candidate lacks it'. Please review the evidence in each report."
)


def build_comparison(
    job: JobRecord, reports: list[AnalysisReport], config: ScoringConfig
) -> ComparisonResult:
    candidates: list[ComparedCandidate] = []
    all_matches = []

    for report in reports:
        # Re-match the candidate's saved resume facts against the job's SAVED requirements.
        matches = match_skills(report.resume, job.parsed)
        score = calculate_score(report.resume, job.parsed, matches, config)
        all_matches.append(matches.matches)

        required = [m for m in matches.matches if m.importance == "required"]
        candidates.append(
            ComparedCandidate(
                analysis_id=report.analysis_id,
                candidate_id=report.storage.candidate_id,
                candidate_name=report.candidate_name,
                analysed_at=report.created_at,
                score=score.value,
                evidence_level=score.evidence_level,
                stored_score=report.score.value,
                score_changed=score.value != report.score.value,
                components=score.components,
                required_supported=sum(1 for m in required if m.status == "supported"),
                required_partial=sum(1 for m in required if m.status == "partial"),
                required_total=len(required),
            )
        )

    # Same job requirements => every candidate's match list has the same skills in the same order.
    rows = [
        SkillComparisonRow(
            name=skill.name,
            importance=skill.importance,
            statuses=[matches[index].status for matches in all_matches],
        )
        for index, skill in enumerate(all_matches[0])
    ]

    notes = [
        "Every candidate was scored against the job's saved requirements with one common "
        "weighting, so the criteria are identical for everyone.",
        "Evidence was verified against each resume when its analysis was created. It is not "
        "re-checked here, because original resumes are not stored.",
    ]
    changed = [c.candidate_name or "Unnamed candidate" for c in candidates if c.score_changed]
    if changed:
        notes.append(
            "The score differs from the original report for: "
            + ", ".join(changed)
            + ". This happens when the original analysis used different weights or a different "
            "reading of the job description."
        )

    return ComparisonResult(
        job_id=job.id,
        job_title=job.title,
        scoring=ComparisonScoring(
            method=SCORING_METHOD,
            weights=normalize_weights(config.weights),
            partial_credit=config.partial_credit,
            entries_for_full_credit=config.entries_for_full_credit,
        ),
        candidates=candidates,
        skills=rows,
        notes=notes,
        disclaimer=DISCLAIMER,
    )