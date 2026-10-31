"""Checks an uploaded file BEFORE we try to read its contents."""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import AppError

ALLOWED_EXTENSIONS: dict[str, Literal["pdf", "txt"]] = {".pdf": "pdf", ".txt": "txt"}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


@dataclass
class ValidatedUpload:
    filename: str  # cleaned, for display only. NEVER used as a file path.
    file_type: Literal["pdf", "txt"]
    data: bytes


def safe_display_name(filename: str | None) -> str:
    """Strip folders and control characters, and limit length."""
    name = re.split(r"[\\/]", filename or "")[-1]
    name = _CONTROL_CHARS.sub("", name).strip()
    return name[:100] or "resume"


def validate_upload_bytes(
    filename: str | None, data: bytes, settings: Settings
) -> ValidatedUpload:
    """Validate extension, size and content of an uploaded file (already read into memory)."""
    display_name = safe_display_name(filename)

    # 1) Extension check
    extension = PurePosixPath(display_name).suffix.lower()
    file_type = ALLOWED_EXTENSIONS.get(extension)
    if file_type is None:
        raise AppError(
            "Unsupported file type. Please upload a PDF (.pdf) or text (.txt) resume.",
            status_code=415,
            code="unsupported_file_type",
        )

    # 2) Size check
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise AppError(
            f"The file is too large. The maximum size is {settings.max_upload_size_mb} MB.",
            status_code=413,
            code="file_too_large",
        )
    if len(data) == 0:
        raise AppError("The uploaded file is empty.", status_code=422, code="empty_file")

    # 3) Content check: a real PDF contains the %PDF- marker at the very start
    if file_type == "pdf" and b"%PDF-" not in data[:1024]:
        raise AppError(
            "This file has a .pdf extension but its contents are not a valid PDF.",
            status_code=422,
            code="file_content_mismatch",
        )

    return ValidatedUpload(filename=display_name, file_type=file_type, data=data)


async def read_and_validate_upload(file: UploadFile, settings: Settings) -> ValidatedUpload:
    """Read at most limit+1 bytes (so oversize files are noticed), then validate."""
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    return validate_upload_bytes(file.filename, data, settings)