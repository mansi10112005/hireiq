"""Checks AI claims against the ORIGINAL text. This is our main hallucination safeguard."""

import re

_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00a0": " ",
}


def normalize_for_match(text: str) -> str:
    """Lowercase, unify fancy quotes/dashes, collapse all whitespace."""
    text = text.lower()
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


class SourceText:
    """The original text (and optionally its sections) used to CHECK what the AI says."""

    def __init__(self, text: str, sections: dict[str, list[str]] | None = None) -> None:
        self._whole = normalize_for_match(text)
        self._sections = {
            name: normalize_for_match(" ".join(lines)) for name, lines in (sections or {}).items()
        }

    @staticmethod
    def _clean(quote: str | None) -> str:
        if not quote:
            return ""
        return normalize_for_match(quote).strip(" \"'-*\u2022.")

    def contains(self, quote: str | None) -> bool:
        """True only if the quote really appears in the text (min. 3 characters)."""
        cleaned = self._clean(quote)
        return len(cleaned) >= 3 and cleaned in self._whole

    def section_of(self, quote: str | None) -> str | None:
        cleaned = self._clean(quote)
        if not cleaned:
            return None
        for name, body in self._sections.items():
            if cleaned in body:
                return name
        return None