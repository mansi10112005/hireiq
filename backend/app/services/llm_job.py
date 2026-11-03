"""Node 4 (AI part): ask the AI about the job description, then VERIFY against the text."""

from app.schemas.evidence import Evidence
from app.schemas.job import ExperienceRequirement, JobSkill, ParsedJobDescription
from app.schemas.llm import LLMJobExtraction
from app.services.evidence_check import SourceText
from app.services.job_parser import JD_HEADINGS
from app.services.llm_client import StructuredLLM
from app.services.prompts import JOB_SYSTEM_PROMPT, wrap_untrusted
from app.services.section_utils import build_heading_map, split_sections
from app.services.skill_names import canonical_skill_name, skill_pattern

_HEADING_MAP = build_heading_map(JD_HEADINGS)


def enhance_job(
    llm: StructuredLLM, job_text: str, base: ParsedJobDescription, max_chars: int
) -> tuple[ParsedJobDescription, list[str]]:
    user = "Extract the data from this job description.\n\n" + wrap_untrusted(
        "job_description", job_text[:max_chars]
    )
    extraction = llm.generate(
        system=JOB_SYSTEM_PROMPT,
        user=user,
        output_model=LLMJobExtraction,
        schema_name="job_extraction",
        max_output_tokens=2500,
    )
    return _merge(llm.model_name, base, extraction, job_text)


def _merge(
    model_name: str, base: ParsedJobDescription, ai: LLMJobExtraction, text: str
) -> tuple[ParsedJobDescription, list[str]]:
    sections = split_sections(text, _HEADING_MAP, first_section="preamble")
    source = SourceText(text, sections)
    dropped = 0

    skills: dict[str, JobSkill] = {
        skill.name.lower(): skill
        for skill in (*base.required_skills, *base.preferred_skills, *base.other_mentioned_skills)
    }

    for item in ai.skills[:60]:
        name = canonical_skill_name(item.name)
        quote = " ".join(item.evidence_quote.split())
        # The quote must exist in the text AND must contain the skill's name.
        if (
            len(name) < 3
            or len(name) > 60
            or not source.contains(quote)
            or not skill_pattern(name).search(quote)
        ):
            dropped += 1
            continue
        evidence = Evidence(
            source="job_description",
            section=source.section_of(quote),
            snippet=quote[:200],
        )
        existing = skills.get(name.lower())
        if existing is None:
            skills[name.lower()] = JobSkill(
                name=name, importance=item.importance, evidence=[evidence]
            )
        elif existing.importance == "unspecified" and item.importance != "unspecified":
            # Headings in the text decide first; the AI may only upgrade "unspecified" skills.
            existing.importance = item.importance
            existing.evidence = [evidence, *existing.evidence][:3]

    responsibilities = base.responsibilities
    if not responsibilities:
        for line in ai.responsibilities[:30]:
            cleaned = " ".join(line.split())
            if len(cleaned) <= 300 and source.contains(cleaned):
                responsibilities.append(cleaned)
            else:
                dropped += 1

    experience_requirements = list(base.experience_requirements)
    if not experience_requirements:
        for item in ai.experience_requirements[:5]:
            quote = " ".join(item.evidence_quote.split())
            if (
                source.contains(quote)
                and 0 <= item.min_years <= 40
                and str(item.min_years) in quote
            ):
                experience_requirements.append(
                    ExperienceRequirement(
                        min_years=item.min_years,
                        max_years=item.max_years,
                        open_ended=item.open_ended,
                        evidence=Evidence(
                            source="job_description",
                            section=source.section_of(quote),
                            snippet=quote[:200],
                        ),
                    )
                )
            else:
                dropped += 1

    all_skills = list(skills.values())
    parsed = ParsedJobDescription(
        parser=f"hybrid_v1:{model_name}",
        title=base.title,
        required_skills=[s for s in all_skills if s.importance == "required"],
        preferred_skills=[s for s in all_skills if s.importance == "preferred"],
        other_mentioned_skills=[s for s in all_skills if s.importance == "unspecified"],
        responsibilities=responsibilities,
        experience_requirements=experience_requirements,
        sections_found=base.sections_found,
        warnings=[w for w in base.warnings if not (all_skills and w.startswith("No skills"))],
    )
    notes: list[str] = []
    if dropped:
        notes.append(
            f"{dropped} AI-extracted job description items were discarded because they could "
            "not be verified in the job text."
        )
    return parsed, notes