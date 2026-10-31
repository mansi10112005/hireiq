"""Shared helpers: splitting text into sections and grouping lines into entries."""

import re

_BULLET_CHARS = "-*\u2022\u2023\u25aa\u25cf\u2013\u00b7"
_BULLET_ONLY = set(_BULLET_CHARS)
_BULLET_PREFIX = re.compile(r"^(?:[" + re.escape(_BULLET_CHARS) + r"]|\d{1,2}[.)])\s+")


def normalize_heading(text: str) -> str:
    """'  TECHNICAL SKILLS: ' -> 'technical skills'."""
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[-/_]", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def build_heading_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """{'skills': ['Skills', 'Technical Skills']} -> {'skills': 'skills', 'technical skills': 'skills'}"""
    return {
        normalize_heading(heading): canonical
        for canonical, headings in groups.items()
        for heading in headings
    }


def strip_bullet(text: str) -> str:
    return _BULLET_PREFIX.sub("", text.strip(), count=1).strip()


def make_snippet(line: str, limit: int = 200) -> str:
    return strip_bullet(line)[:limit]


def _match_heading(line: str, heading_map: dict[str, str]) -> tuple[str | None, str]:
    """If the line is a section heading, return (section_name, text_after_colon)."""
    if not line:
        return None, ""
    if ":" in line:  # e.g. "Skills: Python, SQL"
        label, _, rest = line.partition(":")
        section = heading_map.get(normalize_heading(label))
        if section is not None and len(label) <= 40:
            return section, rest.strip()
        return None, ""
    if len(line) <= 40:
        section = heading_map.get(normalize_heading(line))
        if section is not None:
            return section, ""
    return None, ""


def split_sections(
    text: str, heading_map: dict[str, str], first_section: str
) -> dict[str, list[str]]:
    """Split text into {section_name: [lines]}. Text before any heading goes to first_section."""
    sections: dict[str, list[str]] = {first_section: []}
    current = first_section
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        section, remainder = _match_heading(line, heading_map)
        if section is not None:
            current = section
            sections.setdefault(current, [])
            if remainder:
                sections[current].append(remainder)
        else:
            sections[current].append(line)
    if not any(sections[first_section]):
        del sections[first_section]
    return sections


def group_entries(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Group lines into (heading, detail_lines) entries.

    Rules: a normal line starts a new entry; bullet lines attach to the entry above;
    a line starting with a lowercase letter continues the previous line (PDF line wrapping).
    A lone bullet character on its own line marks the NEXT line as a bullet.
    """
    entries: list[list] = []  # each: [heading, details, heading_was_bullet]
    pending_bullet = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            pending_bullet = False
            continue
        if stripped in _BULLET_ONLY:
            pending_bullet = True
            continue
        is_bullet = pending_bullet or bool(_BULLET_PREFIX.match(stripped))
        pending_bullet = False
        text = strip_bullet(stripped)
        if not text:
            continue
        if is_bullet:
            if entries and not entries[-1][2]:
                entries[-1][1].append(text)
            else:
                entries.append([text, [], True])
        elif entries and text[:1].islower():
            last = entries[-1]
            if last[1]:
                last[1][-1] += " " + text
            else:
                last[0] += " " + text
        else:
            entries.append([text, [], False])
    return [(entry[0], entry[1]) for entry in entries]