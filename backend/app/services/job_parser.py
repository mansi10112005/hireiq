"""Rule-based job-description parser (no AI)."""

import re

from app.schemas.evidence import Evidence
from app.schemas.job import ExperienceRequirement, JobSkill, ParsedJobDescription
from app.services.section_utils import build_heading_map, group_entries, make_snippet, split_sections
from app.services.skills_taxonomy import find_skills
from app.services.text_extraction import normalize_text

JD_HEADINGS: dict[str, list[str]] = {
    "required": [
        "requirements", "required", "required skills", "required qualifications",
        "must have", "must haves", "minimum qualifications", "basic qualifications",
        "what we are looking for", "what you need", "what you bring", "skills required",
        "qualifications",
    ],
    "preferred": [
        "preferred", "preferred skills", "preferred qualifications", "nice to have",
        "nice to haves", "good to have", "bonus", "bonus points", "desirable", "plus points",
    ],
    "responsibilities": [
        "responsibilities", "key responsibilities", "what you will do", "what you'll do",
        "duties", "your responsibilities", "day to day",
    ],
    "other": [
        "about us", "about the role", "about the company", "overview", "company overview",
        "benefits", "what we offer", "perks", "why join us",
    ],
}
_HEADING_MAP = build_heading_map(JD_HEADINGS)

_RANK = {"unspecified": 0, "preferred": 1, "required": 2}
_PREFERRED_CUES = re.compile(
    r"\b(nice to have|good to have|preferred|bonus|a plus|is a plus|desirable|advantage)\b", re.I
)
_REQUIRED_CUES = re.compile(r"\b(must have|must|required|mandatory|essential)\b", re.I)
_YEARS_RE = re.compile(
    r"(?P<min>\d{1,2})\s*(?:[-\u2013]\s*(?P<max>\d{1,2}))?\s*(?P<plus>\+)?\s*(?:years?|yrs?)\b",
    re.I,
)


def _line_importance(section: str, line: str) -> str:
    importance = section if section in ("required", "preferred") else "unspecified"
    if _PREFERRED_CUES.search(line):
        return "preferred"
    if importance == "unspecified" and _REQUIRED_CUES.search(line):
        return "required"
    return importance


def _collect_skills(sections: dict[str, list[str]]) -> dict[str, JobSkill]:
    skills: dict[str, JobSkill] = {}
    for section, lines in sections.items():
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            found = find_skills(line)
            if not found:
                continue
            importance = _line_importance(section, line)
            for name, _matched in found:
                evidence = Evidence(
                    source="job_description", section=section, snippet=make_snippet(line)
                )
                existing = skills.get(name)
                if existing is None:
                    skills[name] = JobSkill(name=name, importance=importance, evidence=[evidence])
                    continue
                upgraded = _RANK[importance] > _RANK[existing.importance]
                if upgraded:
                    existing.importance = importance
                if evidence.snippet not in {e.snippet for e in existing.evidence}:
                    if upgraded:
                        existing.evidence.insert(0, evidence)
                    else:
                        existing.evidence.append(evidence)
                    existing.evidence = existing.evidence[:3]
    return skills


def _find_experience_requirements(sections: dict[str, list[str]]) -> list[ExperienceRequirement]:
    results: list[ExperienceRequirement] = []
    seen: set[str] = set()
    for section, lines in sections.items():
        for raw in lines:
            line = raw.strip()
            if "experience" not in line.lower():
                continue
            match = _YEARS_RE.search(line)
            snippet = make_snippet(line)
            if not match or snippet in seen:
                continue
            seen.add(snippet)
            results.append(
                ExperienceRequirement(
                    min_years=int(match.group("min")),
                    max_years=int(match.group("max")) if match.group("max") else None,
                    open_ended=bool(match.group("plus")),
                    evidence=Evidence(
                        source="job_description", section=section, snippet=snippet
                    ),
                )
            )
    return results[:5]


def parse_job_description(description: str, title: str | None = None) -> ParsedJobDescription:
    text = normalize_text(description)
    sections = split_sections(text, _HEADING_MAP, first_section="preamble")
    sections_found = [name for name in sections if name != "preamble"]

    skills = _collect_skills(sections)
    required = [s for s in skills.values() if s.importance == "required"]
    preferred = [s for s in skills.values() if s.importance == "preferred"]
    other = [s for s in skills.values() if s.importance == "unspecified"]

    responsibilities = [
        " ".join([heading] + details)[:300]
        for heading, details in group_entries(sections.get("responsibilities", []))
    ][:30]

    warnings: list[str] = []
    if "required" not in sections_found and "preferred" not in sections_found:
        warnings.append(
            "No 'Requirements' or 'Nice to have' headings were detected, so skills could not be "
            "classified as required or preferred. Adding such headings improves the result."
        )
    if not skills:
        warnings.append(
            "No skills from HireIQ's skill dictionary were detected in this job description."
        )

    return ParsedJobDescription(
        title=title or None,
        required_skills=required,
        preferred_skills=preferred,
        other_mentioned_skills=other,
        responsibilities=responsibilities,
        experience_requirements=_find_experience_requirements(sections),
        sections_found=sections_found,
        warnings=warnings,
    )