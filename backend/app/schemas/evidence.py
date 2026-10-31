"""Evidence: the exact text a finding came from. Used for traceability."""

from typing import Literal

from pydantic import BaseModel


class Evidence(BaseModel):
    source: Literal["resume", "job_description"]
    section: str | None = None
    snippet: str  # the original line of text (shortened to 200 characters)