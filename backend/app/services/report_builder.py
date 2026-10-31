"""Node 9 logic: assemble the final report. (Scoring and storage are placeholders for now.)"""

from app.schemas.analysis import (
    AnalysisReport,
    CandidateSummary,
    EvaluationResult,
    SkillMatch,
    SkillMatchResult,
    WebIntelligenceResult,
)
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume

LIMITATIONS = [
    "Parsing is rule-based: only skills in HireIQ's skill dictionary are detected, so other skills may be missed.",
    "'Unverified' means the resume gives no evidence of a skill. It does not prove the candidate lacks it.",
    "Years of experience are reported only when the resume states them explicitly.",
    "No match score is calculated yet, and HireIQ never ranks or rejects candidates automatically.",
    "Any AI-generated content added later will be labelled as such and must be validated by a human.",
]


def build_interview_questions(matches: list[SkillMatch]) -> list[str]:
    required_missing = [
        f"The role requires {m.name}. Can you describe any experience you have with it?"
        for m in matches
        if m.importance == "required" and m.status == "unverified"
    ]
    partial = [
        f"Your resume lists {m.name}. Can you walk me through a project or task where you used it?"
        for m in matches
        if m.status == "partial"
    ]
    preferred_missing = [
        f"Have you worked with {m.name}? It is a nice-to-have for this role."
        for m in matches
        if m.importance == "preferred" and m.status == "unverified"
    ]
    return (required_missing + partial + preferred_missing)[:8]


def build_report(
    *,
    analysis_id: str,
    created_at: str,
    job_title: str | None,
    resume: ParsedResume,
    job: ParsedJobDescription,
    summary: CandidateSummary,
    evaluation: EvaluationResult,
    skill_matches: SkillMatchResult,
    web: WebIntelligenceResult | None,
    web_requested: bool,
    warnings: list[str],
    completed_nodes: list[str],
) -> AnalysisReport:
    all_warnings = list(warnings) + resume.warnings + job.warnings

    if web is None:
        if web_requested:
            web = WebIntelligenceResult(
                status="skipped_no_consent",
                note="Web research was requested, but candidate consent was not confirmed, "
                "so no external research was performed.",
            )
            all_warnings.append(
                "Web research was skipped because candidate consent was not confirmed."
            )
        else:
            web = WebIntelligenceResult(
                status="not_requested", note="Web research was not requested."
            )

    return AnalysisReport(
        analysis_id=analysis_id,
        created_at=created_at,
        job_title=job_title,
        candidate_name=resume.contact.name,
        resume=resume,
        job=job,
        summary=summary,
        evaluation=evaluation,
        skill_matches=skill_matches,
        unverified_required_skills=[
            m.name
            for m in skill_matches.matches
            if m.importance == "required" and m.status == "unverified"
        ],
        interview_questions=build_interview_questions(skill_matches.matches),
        web_intelligence=web,
        warnings=list(dict.fromkeys(all_warnings)),  # remove duplicates, keep order
        limitations=LIMITATIONS,
        pipeline=[*completed_nodes, "score_and_store"],
    )