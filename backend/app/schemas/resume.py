"""Data shapes for resume upload, extraction and parsing."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence


class ResumeExtractionResponse(BaseModel):
    filename: str
    file_type: Literal["pdf", "txt"]
    size_bytes: int
    page_count: int | None = Field(None, description="Number of pages (PDF only)")
    char_count: int = Field(description="Characters of text extracted")
    truncated: bool = Field(description="True if the text was cut to the maximum length")
    text_preview: str = Field(description="First 500 characters, for verification only")
    warnings: list[str] = Field(default_factory=list)


class ContactInfo(BaseModel):
    name: str | None = Field(None, description="Best guess from the first lines; may be null")
    email: str | None = None
    phone: str | None = None
    github_url: str | None = Field(None, description="Link as written in the resume; never visited")
    linkedin_url: str | None = Field(None, description="Link as written in the resume; never visited")


class ResumeEntry(BaseModel):
    """One education, experience or project item: a heading line plus its detail lines."""

    heading: str
    details: list[str] = Field(default_factory=list)
    date_range: str | None = Field(None, description="Date range as written, e.g. 'May 2025 - Jul 2025'")


class ResumeSkill(BaseModel):
    name: str  # canonical name from the skill dictionary
    in_skills_section: bool = Field(description="True if the candidate listed it in a Skills section")
    evidence: list[Evidence] = Field(default_factory=list)


class ExperienceStatement(BaseModel):
    """Years of experience ONLY when the resume states it explicitly."""

    years: float
    evidence: Evidence


class ParsedResume(BaseModel):
    parser: str = "rule_based_v1"
    contact: ContactInfo
    summary: str | None = None
    education: list[ResumeEntry] = Field(default_factory=list)
    experience: list[ResumeEntry] = Field(default_factory=list)
    projects: list[ResumeEntry] = Field(default_factory=list)
    skills: list[ResumeSkill] = Field(default_factory=list)
    other_listed_skills: list[str] = Field(
        default_factory=list,
        description="Listed in the Skills section but not in our skill dictionary (unverified)",
    )
    certifications: list[str] = Field(default_factory=list)
    stated_years_of_experience: ExperienceStatement | None = None
    sections_found: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)