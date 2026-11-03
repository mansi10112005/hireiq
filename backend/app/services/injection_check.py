"""Detects text that looks like instructions aimed at an AI. It only WARNS; it never obeys."""

import re

_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
        r"(give|assign|award)\s+(this|the)\s+(candidate|applicant|resume)\b.{0,60}\b(score|rating)",
        r"\b(rate|score)\s+(this|the)\s+(candidate|applicant|resume)\b.{0,40}\b(100|highest|perfect|top)",
        r"you\s+are\s+now\s+(an?\s+)?(ai|assistant|chatbot|language\s+model)",
    )
]


def looks_like_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PATTERNS)


def injection_warning(source: str) -> str:
    return (
        f"The {source} contains text that looks like instructions to an AI system. "
        "It was treated as plain data. HireIQ's safeguards reduce, but cannot fully remove, "
        "the risk of AI manipulation, so please review this report carefully."
    )