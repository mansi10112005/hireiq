"""The deterministic match score. No AI is used here: same inputs, same score, every time."""

import math

from app.schemas.analysis import SkillMatch, SkillMatchResult
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume, ResumeEntry
from app.schemas.scoring import ScoreComponent, ScoreSection, ScoringConfig
from app.services.scoring_config import COMPONENTS, SCORING_METHOD, normalize_weights
from app.services.skill_names import skill_pattern

DISCLAIMER = (
    "This score is a transparent screening aid based on evidence found in the resume. It is not "
    "a hiring decision. HireIQ never ranks, rejects or shortlists candidates automatically, and "
    "a missing skill means 'no evidence found', not 'the candidate lacks it'."
)

Fraction = tuple[float | None, list[str]]  # (0..1 or None if not applicable, explanation lines)


def _entry_text(entry: ResumeEntry) -> str:
    return " ".join([entry.heading, *entry.details])


def _mentioned(text: str, names: list[str]) -> list[str]:
    return [name for name in names if skill_pattern(name).search(text)]


def _skill_fraction(items: list[SkillMatch], credit: dict[str, float]) -> Fraction:
    if not items:
        return None, ["The job description lists no skills of this kind."]
    details = [f"{m.name}: {m.status} (credit {credit[m.status]:g})" for m in items]
    return sum(credit[m.status] for m in items) / len(items), details


def _experience_fraction(
    resume: ParsedResume, job: ParsedJobDescription, names: list[str], config: ScoringConfig
) -> Fraction:
    parts: list[float] = []
    details: list[str] = []

    if names:
        relevant = [e for e in resume.experience if _mentioned(_entry_text(e), names)]
        part = min(1.0, len(relevant) / config.entries_for_full_credit)
        parts.append(part)
        details.append(
            f"{len(relevant)} of {len(resume.experience)} experience entries mention skills from "
            f"the job description (full credit at {config.entries_for_full_credit}): {part:.2f}"
        )

    if job.experience_requirements:
        needed = max(r.min_years for r in job.experience_requirements)
        stated = resume.stated_years_of_experience
        if stated is None:
            details.append(
                f"The job asks for at least {needed} years of experience, but the resume does "
                "not state total years, so this was not scored (no penalty)."
            )
        else:
            ratio = 1.0 if needed <= 0 else min(1.0, stated.years / needed)
            parts.append(ratio)
            details.append(
                f"The resume states {stated.years:g} years; the job asks for {needed}: {ratio:.2f}"
            )

    if not parts:
        return None, details or ["The job description gives nothing to compare experience with."]
    return sum(parts) / len(parts), details


def _projects_fraction(resume: ParsedResume, names: list[str], config: ScoringConfig) -> Fraction:
    if not names:
        return None, ["The job description lists no recognised skills to compare with."]
    projects = [p for p in resume.projects if _mentioned(_entry_text(p), names)]
    certifications = [c for c in resume.certifications if _mentioned(c, names)]
    count = len(projects) + len(certifications)
    fraction = min(1.0, count / config.entries_for_full_credit)
    details = [
        f"{len(projects)} of {len(resume.projects)} projects and {len(certifications)} of "
        f"{len(resume.certifications)} certifications mention skills from the job description "
        f"(full credit at {config.entries_for_full_credit}): {fraction:.2f}"
    ]
    return fraction, details


def calculate_score(
    resume: ParsedResume,
    job: ParsedJobDescription,
    matches: SkillMatchResult,
    config: ScoringConfig,
) -> ScoreSection:
    credit = {"supported": 1.0, "partial": config.partial_credit, "unverified": 0.0}
    all_matches = matches.matches
    names = [m.name for m in all_matches]
    required = [m for m in all_matches if m.importance == "required"]
    preferred = [m for m in all_matches if m.importance == "preferred"]
    unscored = [m for m in all_matches if m.importance == "unspecified"]

    results: dict[str, Fraction] = {
        "required_skills": _skill_fraction(required, credit),
        "preferred_skills": _skill_fraction(preferred, credit),
        "experience": _experience_fraction(resume, job, names, config),
        "projects_qualifications": _projects_fraction(resume, names, config),
    }

    weights = normalize_weights(config.weights)  # now they add up to 100
    weight_of = weights.model_dump()

    # Criteria that have data AND a weight above zero share the 100 points.
    active = {
        key for key, (fraction, _) in results.items() if fraction is not None and weight_of[key] > 0
    }
    active_total = sum(weight_of[key] for key in active)

    components: list[ScoreComponent] = []
    exact = 0.0
    for key, label, description in COMPONENTS:
        fraction, details = results[key]
        effective = weight_of[key] / active_total * 100 if key in active else 0.0
        points = (fraction or 0.0) * effective
        exact += points
        components.append(
            ScoreComponent(
                key=key,  # type: ignore[arg-type]
                label=label,
                applicable=fraction is not None,
                fraction=None if fraction is None else round(fraction, 4),
                configured_weight=round(weight_of[key], 2),
                effective_weight=round(effective, 2),
                points=round(points, 2),
                explanation=description,
                details=details,
            )
        )

    calculated = active_total > 0
    notes: list[str] = []
    if calculated:
        without_data = [c.label for c in components if not c.applicable]
        if without_data:
            notes.append(
                "No data in the job description for: "
                + ", ".join(without_data)
                + ". Their weight was shared proportionally among the other criteria."
            )
    else:
        notes.append(
            "No score was calculated because none of the criteria with a weight above zero had "
            "data in the job description."
        )
    if unscored:
        notes.append(
            f"{len(unscored)} skills of unspecified importance were not scored: "
            + ", ".join(m.name for m in unscored)
            + "."
        )
    notes.append("Education is not scored yet.")

    value = max(1, min(100, math.floor(exact + 0.5))) if calculated else None
    level = None
    if value is not None:
        level = "strong" if value >= 75 else "moderate" if value >= 50 else "limited"

    return ScoreSection(
        status="calculated" if calculated else "not_calculated",
        value=value,
        exact=round(exact, 2) if calculated else None,
        evidence_level=level,
        method=SCORING_METHOD,
        weights=weights,
        partial_credit=config.partial_credit,
        entries_for_full_credit=config.entries_for_full_credit,
        components=components,
        notes=notes,
        disclaimer=DISCLAIMER,
    )