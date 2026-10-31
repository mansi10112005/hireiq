"""Node 5 logic: a template-based candidate summary built ONLY from the parsed resume."""

from app.schemas.analysis import CandidateSummary, SummaryStatement
from app.schemas.evidence import Evidence
from app.schemas.resume import ParsedResume, ResumeEntry


def _statement_from_entry(section: str, entry: ResumeEntry) -> SummaryStatement:
    return SummaryStatement(
        text=entry.heading,
        origin="resume",
        evidence=[Evidence(source="resume", section=section, snippet=entry.heading[:200])],
    )


def build_candidate_summary(resume: ParsedResume) -> CandidateSummary:
    professional = None
    if resume.summary:
        professional = SummaryStatement(
            text=resume.summary,
            origin="resume",
            evidence=[Evidence(source="resume", section="summary", snippet=resume.summary[:200])],
        )

    # Strengths: skills that appear somewhere other than the Skills list (i.e. shown in use).
    strengths: list[SummaryStatement] = []
    for skill in resume.skills:
        outside = [e for e in skill.evidence if e.section != "skills"]
        if outside:
            places = sorted({e.section or "resume" for e in outside})
            strengths.append(
                SummaryStatement(
                    text=f"{skill.name} (appears in: {', '.join(places)})",
                    origin="derived",
                    evidence=outside,
                )
            )

    return CandidateSummary(
        professional_summary=professional,
        experience_overview=[_statement_from_entry("experience", e) for e in resume.experience[:5]],
        education_overview=[_statement_from_entry("education", e) for e in resume.education[:3]],
        project_overview=[_statement_from_entry("projects", e) for e in resume.projects[:5]],
        key_strengths=strengths[:8],
    )