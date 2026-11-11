"""Scoring settings, the description of each criterion, and the human-readable rules."""

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.scoring import ComponentInfo, ScoringConfig, ScoringInfo, ScoringWeights

SCORING_METHOD = "weighted_evidence_v1"

# (key, label, description): the order here is the order shown in the report
COMPONENTS: list[tuple[str, str, str]] = [
    (
        "required_skills",
        "Required skill coverage",
        "How much of the job's required skills the resume evidences. A skill shown in use "
        "(experience, projects...) earns full credit, a skill only listed in the Skills section "
        "earns partial credit, and a skill with no evidence earns zero.",
    ),
    (
        "preferred_skills",
        "Preferred skill coverage",
        "The same rule, applied to the job's preferred (nice-to-have) skills.",
    ),
    (
        "experience",
        "Relevant experience",
        "The share of experience entries that mention skills from the job description (full "
        "credit at the configured number of entries), averaged with a years-of-experience check "
        "only when the resume states total years and the job asks for a minimum.",
    ),
    (
        "projects_qualifications",
        "Relevant projects and qualifications",
        "Projects and certifications that mention skills from the job description (full credit "
        "at the configured number of items).",
    ),
]

RULES = [
    "The score is calculated by plain Python arithmetic on evidence found in the resume. "
    "No AI decides or adjusts it.",
    "Each criterion gets a fraction between 0 and 1. Fraction x effective weight = points. "
    "The points add up to a score out of 100, rounded to a whole number and never below 1.",
    "Weights are relative: they are scaled so that they add up to 100.",
    "A criterion for which the job description gives no data (for example, no preferred skills) "
    "is not applicable; its weight is shared proportionally among the other criteria.",
    "A skill with no evidence earns zero. This means 'no evidence found', not 'the candidate "
    "lacks the skill'.",
    "Evidence is checked against the original text before scoring; evidence that cannot be found "
    "there is not counted.",
]

LIMITATIONS = [
    "Education is not scored yet.",
    "Skills of unspecified importance in the job description are not scored.",
    "Total career length is not calculated from dates; years of experience count only when the "
    "resume states them.",
    "Related skills (for example PostgreSQL for a SQL requirement) are not credited yet.",
    "The score is a screening aid, not a hiring decision.",
]


def normalize_weights(weights: ScoringWeights) -> ScoringWeights:
    """Scale the weights so that they add up to 100."""
    values = weights.model_dump()
    total = sum(values.values())
    if total <= 0:
        raise AppError(
            "At least one scoring weight must be greater than zero.",
            status_code=422,
            code="invalid_scoring_weights",
        )
    return ScoringWeights(**{key: value / total * 100 for key, value in values.items()})


def default_scoring_config(settings: Settings) -> ScoringConfig:
    return ScoringConfig(
        weights=ScoringWeights(
            required_skills=settings.score_weight_required_skills,
            preferred_skills=settings.score_weight_preferred_skills,
            experience=settings.score_weight_experience,
            projects_qualifications=settings.score_weight_projects_qualifications,
        ),
        partial_credit=settings.score_partial_credit,
        entries_for_full_credit=settings.score_entries_for_full_credit,
    )


def build_scoring_config(settings: Settings, overrides: dict[str, float | None]) -> ScoringConfig:
    """Defaults from settings, with any per-request weights on top. Fails fast on bad input."""
    config = default_scoring_config(settings)
    weights = config.weights.model_dump()
    for key, value in overrides.items():
        if value is not None:
            weights[key] = value
    new_weights = ScoringWeights(**weights)
    normalize_weights(new_weights)  # raises if every weight is zero
    return config.model_copy(update={"weights": new_weights})


def describe_scoring(config: ScoringConfig) -> ScoringInfo:
    return ScoringInfo(
        method=SCORING_METHOD,
        weights=normalize_weights(config.weights),
        partial_credit=config.partial_credit,
        entries_for_full_credit=config.entries_for_full_credit,
        components=[
            ComponentInfo(key=key, label=label, description=description)
            for key, label, description in COMPONENTS
        ],
        rules=RULES,
        limitations=LIMITATIONS,
    )