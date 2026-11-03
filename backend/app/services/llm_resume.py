"""Node 3 (AI part): ask the AI about the resume, then VERIFY everything against the text."""

import re

from app.schemas.evidence import Evidence
from app.schemas.llm import LLMEntry, LLMResumeExtraction
from app.schemas.resume import (
    ContactInfo,
    ExperienceStatement,
    ParsedResume,
    ResumeEntry,
    ResumeSkill,
)
from app.services.evidence_check import SourceText
from app.services.llm_client import StructuredLLM
from app.services.prompts import RESUME_SYSTEM_PROMPT, wrap_untrusted
from app.services.resume_parser import RESUME_HEADINGS
from app.services.section_utils import build_heading_map, split_sections
from app.services.skill_names import canonical_skill_name, collect_evidence

_HEADING_MAP = build_heading_map(RESUME_HEADINGS)


def resume_sections(text: str) -> dict[str, list[str]]:
    return split_sections(text, _HEADING_MAP, first_section="header")


def enhance_resume(
    llm: StructuredLLM, text: str, base: ParsedResume, max_chars: int
) -> tuple[ParsedResume, list[str]]:
    user = "Extract the data from this resume.\n\n" + wrap_untrusted("resume_text", text[:max_chars])
    extraction = llm.generate(
        system=RESUME_SYSTEM_PROMPT,
        user=user,
        output_model=LLMResumeExtraction,
        schema_name="resume_extraction",
        max_output_tokens=3000,
    )
    return _merge(llm.model_name, base, extraction, text)


def _valid_email(value: str | None) -> str | None:
    if value and "@" in value and "." in value.split("@")[-1]:
        return value
    return None


def _valid_phone(value: str | None) -> str | None:
    if value and 10 <= len(re.sub(r"\D", "", value)) <= 13:
        return value
    return None


def _merge(
    model_name: str, base: ParsedResume, ai: LLMResumeExtraction, text: str
) -> tuple[ParsedResume, list[str]]:
    sections = resume_sections(text)
    source = SourceText(text, sections)
    dropped = 0

    def verified(value: str | None, max_len: int) -> str | None:
        """Return the value only if it really appears in the resume."""
        nonlocal dropped
        if value is None or not value.strip():
            return None
        value = " ".join(value.split())
        if len(value) <= max_len and source.contains(value):
            return value
        dropped += 1
        return None

    def verified_entries(entries: list[LLMEntry]) -> list[ResumeEntry]:
        result: list[ResumeEntry] = []
        for entry in entries[:20]:
            heading = verified(entry.heading, 300)
            if heading is None:
                continue
            details = [d for d in (verified(d, 500) for d in entry.details[:15]) if d]
            result.append(
                ResumeEntry(
                    heading=heading,
                    details=details,
                    date_range=verified(entry.date_range, 60),
                )
            )
        return result

    # --- Contact: rule-based values win; the AI only fills gaps (and must be verifiable) ---
    contact = ContactInfo(
        name=base.contact.name or verified(ai.name, 60),
        email=base.contact.email or _valid_email(verified(ai.email, 100)),
        phone=base.contact.phone or _valid_phone(verified(ai.phone, 30)),
        github_url=base.contact.github_url,
        linkedin_url=base.contact.linkedin_url,
    )
    summary = base.summary or verified(ai.summary, 1000)

    # --- Entries: verified AI entries are preferred (better at odd layouts), else rule-based ---
    education = verified_entries(ai.education) or base.education
    experience = verified_entries(ai.experience) or base.experience
    projects = verified_entries(ai.projects) or base.projects

    # --- Skills: keep all rule-based skills, add AI skills only if proven by the text ---
    skills = list(base.skills)
    known = {skill.name.lower() for skill in skills}
    for item in ai.skills[:60]:
        name = canonical_skill_name(item.name)
        # Very short names ("C", "R", "Go") match ordinary words, so we ignore them.
        if len(name) < 3 or len(name) > 60 or name.lower() in known:
            continue
        if not source.contains(item.evidence_quote):
            dropped += 1
            continue
        evidence = collect_evidence(name, sections, "resume")  # real lines from the text
        if not evidence:
            dropped += 1
            continue
        known.add(name.lower())
        skills.append(
            ResumeSkill(
                name=name,
                in_skills_section=any(e.section == "skills" for e in evidence),
                evidence=evidence,
            )
        )

    # --- Years of experience: only if the resume literally states it ---
    stated = base.stated_years_of_experience
    quote = ai.stated_years_quote
    if stated is None and ai.stated_years_of_experience is not None:
        years = ai.stated_years_of_experience
        if quote and source.contains(quote) and 0 < years <= 50 and f"{years:g}" in quote:
            stated = ExperienceStatement(
                years=years,
                evidence=Evidence(
                    source="resume",
                    section=source.section_of(quote),
                    snippet=" ".join(quote.split())[:200],
                ),
            )
        else:
            dropped += 1

    certifications = base.certifications or [
        c for c in (verified(c, 200) for c in ai.certifications[:20]) if c
    ]
    other_listed = [t for t in base.other_listed_skills if t.lower() not in known]

    # --- Recompute which fields are still missing ---
    missing: list[str] = []
    for field_name, value in (("name", contact.name), ("email", contact.email), ("phone", contact.phone)):
        if value is None:
            missing.append(field_name)
    for field_name, value in (
        ("summary", summary),
        ("education", education),
        ("experience", experience),
        ("projects", projects),
        ("skills", skills),
        ("certifications", certifications),
    ):
        if not value:
            missing.append(field_name)

    warnings = [w for w in base.warnings if not (skills and w.startswith("No skills"))]

    parsed = ParsedResume(
        parser=f"hybrid_v1:{model_name}",
        contact=contact,
        summary=summary,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        other_listed_skills=other_listed,
        certifications=certifications,
        stated_years_of_experience=stated,
        sections_found=base.sections_found,
        missing_fields=missing,
        warnings=warnings,
    )
    notes: list[str] = []
    if dropped:
        notes.append(
            f"{dropped} AI-extracted resume items were discarded because they could not be "
            "verified in the resume text."
        )
    return parsed, notes