"""Turns validated file bytes into clean text. Pure functions: easy to test on their own."""

import re
from dataclasses import dataclass, field
from typing import Literal

import pymupdf

from app.core.config import Settings
from app.core.errors import AppError

# Control characters except tab (\x09), newline (\x0a) and carriage return (\x0d)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class ExtractionResult:
    text: str
    page_count: int | None
    truncated: bool
    warnings: list[str] = field(default_factory=list)


def normalize_text(raw: str) -> str:
    """Remove junk characters and tidy whitespace."""
    text = _CONTROL_CHARS.sub("", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)  # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)  # many blank lines -> one
    return text.strip()


def _apply_length_limit(text: str, settings: Settings) -> tuple[str, bool, list[str]]:
    if len(text) > settings.max_resume_chars:
        warning = (
            f"The resume text was longer than {settings.max_resume_chars} characters "
            "and was shortened."
        )
        return text[: settings.max_resume_chars], True, [warning]
    return text, False, []


def extract_text_from_pdf(data: bytes, settings: Settings) -> ExtractionResult:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise AppError(
            "The PDF could not be opened. It may be corrupted.",
            status_code=422,
            code="invalid_pdf",
        ) from exc

    try:
        if doc.needs_pass:
            raise AppError(
                "This PDF is password-protected. Please upload an unlocked copy.",
                status_code=422,
                code="password_protected_pdf",
            )
        page_count = doc.page_count
        if page_count > settings.max_pdf_pages:
            raise AppError(
                f"This PDF has {page_count} pages. The maximum is {settings.max_pdf_pages}.",
                status_code=422,
                code="too_many_pages",
            )
        pages = [page.get_text("text") for page in doc]
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "Text could not be read from this PDF.",
            status_code=422,
            code="invalid_pdf",
        ) from exc
    finally:
        doc.close()

    text = normalize_text("\n\n".join(pages))
    if len(text) < settings.min_resume_chars:
        raise AppError(
            "This PDF contains little or no selectable text. It may be a scanned image. "
            "Reading scanned documents requires OCR (text recognition from images), which "
            "HireIQ does not support yet. Please upload a text-based PDF or a .txt version.",
            status_code=422,
            code="ocr_required",
        )

    text, truncated, warnings = _apply_length_limit(text, settings)
    return ExtractionResult(text=text, page_count=page_count, truncated=truncated, warnings=warnings)


def extract_text_from_txt(data: bytes, settings: Settings) -> ExtractionResult:
    if b"\x00" in data:
        raise AppError(
            "This does not look like a plain-text file. Save it as UTF-8 text and try again.",
            status_code=422,
            code="invalid_text_file",
        )
    try:
        raw = data.decode("utf-8-sig")  # handles UTF-8 with or without BOM
    except UnicodeDecodeError:
        raw = data.decode("cp1252", errors="replace")  # common Windows Notepad encoding

    text = normalize_text(raw)
    if len(text) < settings.min_resume_chars:
        raise AppError(
            "The document contains too little text to analyze.",
            status_code=422,
            code="empty_document",
        )

    text, truncated, warnings = _apply_length_limit(text, settings)
    return ExtractionResult(text=text, page_count=None, truncated=truncated, warnings=warnings)


def extract_text(
    data: bytes, file_type: Literal["pdf", "txt"], settings: Settings
) -> ExtractionResult:
    if file_type == "pdf":
        return extract_text_from_pdf(data, settings)
    return extract_text_from_txt(data, settings)