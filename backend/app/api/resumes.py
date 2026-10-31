"""Resume endpoints: extract text, and parse into structured data."""

import logging

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.schemas.common import ErrorResponse
from app.schemas.resume import ParsedResume, ResumeExtractionResponse
from app.services.resume_parser import parse_resume
from app.services.text_extraction import ExtractionResult, extract_text
from app.utils.file_validation import ValidatedUpload, read_and_validate_upload

logger = logging.getLogger("hireiq")

router = APIRouter(prefix="/resumes", tags=["Resumes"])

_ERROR_RESPONSES = {
    413: {"model": ErrorResponse, "description": "File too large"},
    415: {"model": ErrorResponse, "description": "Unsupported file type"},
    422: {"model": ErrorResponse, "description": "Unreadable, empty, or scanned document"},
}


async def _load_resume(
    file: UploadFile, settings: Settings
) -> tuple[ValidatedUpload, ExtractionResult]:
    """Validate the upload, then extract its text. Shared by both endpoints."""
    upload = await read_and_validate_upload(file, settings)
    # PDF parsing is CPU work; run it in a worker thread so the server stays responsive.
    result = await run_in_threadpool(extract_text, upload.data, upload.file_type, settings)
    return upload, result


@router.post(
    "/extract",
    response_model=ResumeExtractionResponse,
    summary="Upload a resume (PDF or TXT) and extract its text",
    responses=_ERROR_RESPONSES,
)
async def extract_resume(
    file: UploadFile = File(..., description="A .pdf or .txt resume"),
    settings: Settings = Depends(get_settings),
) -> ResumeExtractionResponse:
    upload, result = await _load_resume(file, settings)

    # Log METADATA ONLY. Never log resume text.
    logger.info(
        "Resume extracted: type=%s size=%d pages=%s chars=%d",
        upload.file_type,
        len(upload.data),
        result.page_count,
        len(result.text),
    )

    return ResumeExtractionResponse(
        filename=upload.filename,
        file_type=upload.file_type,
        size_bytes=len(upload.data),
        page_count=result.page_count,
        char_count=len(result.text),
        truncated=result.truncated,
        text_preview=result.text[:500],
        warnings=result.warnings,
    )


@router.post(
    "/parse",
    response_model=ParsedResume,
    summary="Upload a resume and get structured, evidence-backed data",
    responses=_ERROR_RESPONSES,
)
async def parse_resume_endpoint(
    file: UploadFile = File(..., description="A .pdf or .txt resume"),
    settings: Settings = Depends(get_settings),
) -> ParsedResume:
    upload, result = await _load_resume(file, settings)
    parsed = await run_in_threadpool(parse_resume, result.text)
    parsed.warnings = result.warnings + parsed.warnings

    # Counts only, never personal data or resume text.
    logger.info(
        "Resume parsed: type=%s sections=%d skills=%d",
        upload.file_type,
        len(parsed.sections_found),
        len(parsed.skills),
    )
    return parsed