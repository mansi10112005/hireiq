"""Helpers for skill names: canonical spelling and finding evidence lines in the text."""

import re
from typing import Literal

from app.schemas.evidence import Evidence
from app.services.section_utils import make_snippet
from app.services.skills_taxonomy import SKILL_ALIASES

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for alias in aliases
}
_ALIAS_TO_CANONICAL.update({canonical.lower(): canonical for canonical in SKILL_ALIASES})


def canonical_skill_name(raw: str) -> str:
    """'REST API' -> 'REST APIs'. Unknown skills keep their own (tidied) spelling."""
    cleaned = " ".join(raw.split()).strip(" .,;:")
    return _ALIAS_TO_CANONICAL.get(cleaned.lower(), cleaned)


def skill_pattern(name: str) -> re.Pattern[str]:
    aliases = {*SKILL_ALIASES.get(name, []), name}
    body = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
    return re.compile(r"(?<![A-Za-z0-9+#])(?:" + body + r")(?![A-Za-z0-9+#])", re.IGNORECASE)


def collect_evidence(
    name: str,
    sections: dict[str, list[str]],
    source: Literal["resume", "job_description"],
    limit: int = 3,
) -> list[Evidence]:
    """Find up to `limit` real lines of text that mention the skill."""
    pattern = skill_pattern(name)
    found: list[Evidence] = []
    for section, lines in sections.items():
        for raw in lines:
            line = raw.strip()
            if not line or not pattern.search(line):
                continue
            snippet = make_snippet(line)
            if snippet in {e.snippet for e in found}:
                continue
            found.append(Evidence(source=source, section=section, snippet=snippet))
            if len(found) >= limit:
                return found
    return found