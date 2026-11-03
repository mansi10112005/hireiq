"""Checks that the Groq key, model and structured output work.

Run from the backend folder:  python -m scripts.check_groq
"""

from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.services.llm_client import GroqStructuredLLM, LLMUnavailableError


class Ping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    language: str


def main() -> int:
    settings = get_settings()
    if not settings.groq_configured:
        print("GROQ_API_KEY is missing or still a placeholder in backend\\.env")
        return 1

    print(f"Calling Groq model: {settings.groq_model} ...")
    llm = GroqStructuredLLM(settings)
    try:
        result = llm.generate(
            system="Reply with JSON only.",
            user="What is the capital of France? Also say which language your answer is in.",
            output_model=Ping,
            schema_name="ping",
            max_output_tokens=800,
        )
    except LLMUnavailableError as exc:
        print(f"FAILED: {exc}")
        return 1

    print("OK:", result.model_dump())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())