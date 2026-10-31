"""Rule-based resume parser (no AI). Same text in -> same result out."""

import re

from app.schemas.evidence import Evidence
from app.schemas.resume import (
    ContactInfo,
    ExperienceStatement,
    ParsedResume,
    ResumeEntry,
    ResumeSkill,
)
from app.services.section_utils import (
    build_heading_map,
    group_entries,
    make_snippet,
    split_sections,
    strip_bullet,
)
from app.services.skills_taxonomy import find_skills

RESUME_HEADINGS: dict[str, list[str]] = {
    "summary": [
        "summary", "professional summary", "career summary", "profile",
        "professional profile", "objective", "career objective", "about me", "about",
    ],
    "education": [
        "education", "academic background", "academic qualifications",
        "educational qualifications", "education and qualifications",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment history",
        "work history", "internships", "internship experience", "employment",
        "relevant experience",
    ],
    "projects": [
        "projects", "academic projects", "personal projects", "key projects",
        "project work", "selected projects",
    ],
    "skills": [
        "skills", "technical skills", "key skills", "core skills", "core competencies",
        "skills and tools", "technical proficiencies", "tech stack", "technologies",
    ],
    "certifications": [
        "certifications", "certificates", "licenses and certifications",
        "courses and certifications", "courses", "training and certifications",
    ],
}
_HEADING_MAP = build_heading_map(RESUME_HEADINGS)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d ().-]{8,16}\d(?!\w)")
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+", re.I)
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%-]+", re.I)

_DATE = (
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}"
)
_DATE_RANGE_RE = re.compile(
    r"(?:" + _DATE + r")\s*(?:[-\u2013\u2014]|\bto\b)\s*(?:" + _DATE + r"|present|current|now)",
    re.I,
)

_STATED_YEARS_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?"
    r"(?:(?:professional|work|industry|relevant|hands-on)\s+)?experience",
    re.I,
)

_NAME_STOP_WORDS = ("resume", "curriculum", "vitae")


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _find_phone(text: str) -> str | None:
    for match in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits) <= 13:
            return match.group(0).strip()
    return None


def _guess_name(header_lines: list[str]) -> str | None:
    """Heuristic: the first short, letters-only line of 2-4 words. May return None."""
    for line in header_lines[:6]:
        candidate = line.strip()
        if not candidate or len(candidate) > 50:
            continue
        lowered = candidate.lower()
        if "@" in candidate or "http" in lowered or any(ch.isdigit() for ch in candidate):
            continue
        if any(word in lowered for word in _NAME_STOP_WORDS):
            continue
        words = candidate.split()
        if 2 <= len(words) <= 4 and all(
            w.replace(".", "").replace("'", "").replace("-", "").isalpha() for w in words
        ):
            return candidate
    return None


def _build_entries(lines: list[str]) -> list[ResumeEntry]:
    entries: list[ResumeEntry] = []
    for heading, details in group_entries(lines):
        date_range = _first_match(_DATE_RANGE_RE, " ".join([heading] + details))
        entries.append(
            ResumeEntry(
                heading=heading[:300],
                details=[d[:500] for d in details[:15]],
                date_range=date_range,
            )
        )
    return entries[:20]


def _listed_skill_tokens(lines: list[str]) -> list[str]:
    tokens: list[str] = []
    for line in lines:
        text = strip_bullet(line)
        if not text:
            continue
        label, sep, rest = text.partition(":")
        if sep and len(label) <= 30 and "," not in label:  # "Languages: Python, Java"
            text = rest
        for token in re.split(r"[,;|\u2022]", text):
            token = token.strip(" .\t")
            if token and len(token) <= 40 and len(token.split()) <= 4:
                tokens.append(token)
    return tokens


def _extract_skills(sections: dict[str, list[str]]) -> tuple[list[ResumeSkill], list[str]]:
    found: dict[str, ResumeSkill] = {}
    for section, lines in sections.items():
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            for name, _matched in find_skills(line):
                skill = found.get(name)
                if skill is None:
                    skill = ResumeSkill(name=name, in_skills_section=False)
                    found[name] = skill
                if section == "skills":
                    skill.in_skills_section = True
                snippet = make_snippet(line)
                if len(skill.evidence) < 3 and snippet not in {e.snippet for e in skill.evidence}:
                    skill.evidence.append(
                        Evidence(source="resume", section=section, snippet=snippet)
                    )

    other: list[str] = []
    seen: set[str] = set()
    for token in _listed_skill_tokens(sections.get("skills", [])):
        if find_skills(token) or token.lower() in seen:
            continue
        seen.add(token.lower())
        other.append(token)
    return list(found.values()), other[:30]


def _find_stated_years(sections: dict[str, list[str]]) -> ExperienceStatement | None:
    for section, lines in sections.items():
        for raw in lines:
            match = _STATED_YEARS_RE.search(raw)
            if match:
                return ExperienceStatement(
                    years=float(match.group(1)),
                    evidence=Evidence(
                        source="resume", section=section, snippet=make_snippet(raw)
                    ),
                )
    return None


def parse_resume(text: str) -> ParsedResume:
    sections = split_sections(text, _HEADING_MAP, first_section="header")
    header_lines = sections.get("header", [])
    header_text = "\n".join(header_lines)
    sections_found = [name for name in sections if name != "header"]

    contact = ContactInfo(
        name=_guess_name(header_lines),
        email=_first_match(_EMAIL_RE, header_text) or _first_match(_EMAIL_RE, text),
        phone=_find_phone(header_text),
        github_url=_first_match(_GITHUB_RE, header_text) or _first_match(_GITHUB_RE, text),
        linkedin_url=_first_match(_LINKEDIN_RE, header_text) or _first_match(_LINKEDIN_RE, text),
    )

    summary_text = " ".join(line.strip() for line in sections.get("summary", []) if line.strip())
    summary = summary_text[:1000] or None

    education = _build_entries(sections.get("education", []))
    experience = _build_entries(sections.get("experience", []))
    projects = _build_entries(sections.get("projects", []))
    certifications = [
        " ".join([heading] + details)[:200]
        for heading, details in group_entries(sections.get("certifications", []))
    ][:20]
    skills, other_listed = _extract_skills(sections)
    stated_years = _find_stated_years(sections)

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

    warnings: list[str] = []
    if not sections_found:
        warnings.append(
            "No standard section headings (Skills, Experience, Education...) were detected, "
            "so education, experience and projects could not be separated."
        )
    if not skills:
        warnings.append(
            "No skills from HireIQ's skill dictionary were detected. "
            "This does not mean the candidate has none."
        )

    return ParsedResume(
        contact=contact,
        summary=summary,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        other_listed_skills=other_listed,
        certifications=certifications,
        stated_years_of_experience=stated_years,
        sections_found=sections_found,
        missing_fields=missing,
        warnings=warnings,
    )