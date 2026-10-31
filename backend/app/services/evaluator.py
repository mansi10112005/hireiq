"""Node 6 logic: a MOCK evaluator (rule-based). Milestone 7 adds an LLM-based version
that must return the same EvaluationResult shape."""

from app.schemas.analysis import EvaluationResult, ExperienceCheck, RelevantEntry
from app.schemas.evidence import Evidence
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume
from app.services.skills_taxonomy import find_skills


def evaluate_candidate(resume: ParsedResume, job: ParsedJobDescription) -> EvaluationResult:
    wanted = {
        skill.name
        for skill in (*job.required_skills, *job.preferred_skills, *job.other_mentioned_skills)
    }

    relevant: list[RelevantEntry] = []
    for section, entries in (("experience", resume.experience), ("projects", resume.projects)):
        for entry in entries:
            matched: list[str] = []
            first_line: str | None = None
            for line in [entry.heading, *entry.details]:
                names = [name for name, _ in find_skills(line) if name in wanted]
                if names and first_line is None:
                    first_line = line
                for name in names:
                    if name not in matched:
                        matched.append(name)
            if matched and first_line:
                relevant.append(
                    RelevantEntry(
                        section=section,
                        heading=entry.heading[:200],
                        matched_skills=matched,
                        evidence=Evidence(
                            source="resume", section=section, snippet=first_line[:200]
                        ),
                    )
                )

    checks: list[ExperienceCheck] = []
    stated = resume.stated_years_of_experience
    for requirement in job.experience_requirements:
        if stated is None:
            status, note = (
                "unverified",
                "The resume does not state total years of experience, and HireIQ does not "
                "guess them from dates yet.",
            )
        elif stated.years >= requirement.min_years:
            status, note = "meets_stated", "The resume states at least this many years."
        else:
            status, note = "below_stated", "The resume states fewer years than required."
        checks.append(
            ExperienceCheck(
                requirement=requirement.evidence.snippet,
                min_years=requirement.min_years,
                stated_years=stated.years if stated else None,
                status=status,
                note=note,
            )
        )

    notes = [
        f"{len(relevant)} experience/project entries mention skills that appear in the job "
        "description."
    ]
    return EvaluationResult(relevant_entries=relevant, experience_checks=checks, notes=notes)