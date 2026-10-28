"""Data shapes for resume upload and extraction."""

from typing import Literal

from pydantic import BaseModel, Field


class ResumeExtractionResponse(BaseModel):
    filename: str
    file_type: Literal["pdf", "txt"]
    size_bytes: int
    page_count: int | None = Field(None, description="Number of pages (PDF only)")
    char_count: int = Field(description="Characters of text extracted")
    truncated: bool = Field(description="True if the text was cut to the maximum length")
    text_preview: str = Field(description="First 500 characters, for verification only")
    warnings: list[str] = Field(default_factory=list)