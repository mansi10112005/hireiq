"""A thin wrapper around the Groq API that returns VALIDATED Pydantic objects.

Safety rules in this file:
  - the reply is validated against our schema; invalid replies are retried once
  - every failure becomes LLMUnavailableError, whose message never contains document text
  - we log only counts and timings, never prompts or replies
"""

import logging
import time
from functools import lru_cache
from typing import Any, Protocol, TypeVar

import groq
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

logger = logging.getLogger("hireiq")

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    """The AI could not give a usable answer. The message is safe to show to users."""


class StructuredLLM(Protocol):
    model_name: str

    def generate(
        self,
        *,
        system: str,
        user: str,
        output_model: type[T],
        schema_name: str,
        max_output_tokens: int = 1500,
    ) -> T: ...


class GroqStructuredLLM:
    def __init__(self, settings: Settings, client: Any = None) -> None:
        self.model_name = settings.groq_model
        self._strict = settings.groq_strict_schema
        self._reasoning_effort = (settings.groq_reasoning_effort or "").strip() or None
        # The Groq SDK itself retries rate-limit (429) and temporary server errors
        # with waiting, up to max_retries times.
        self._client = client or groq.Groq(
            api_key=settings.groq_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    def generate(
        self,
        *,
        system: str,
        user: str,
        output_model: type[T],
        schema_name: str,
        max_output_tokens: int = 1500,
    ) -> T:
        schema = output_model.model_json_schema()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        extra_body = (
            {"reasoning_effort": self._reasoning_effort} if self._reasoning_effort else None
        )
        problem = "unknown problem"

        for attempt in (1, 2):  # first try + one retry for unusable replies
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "strict": self._strict,
                            "schema": schema,
                        },
                    },
                    temperature=0.1,
                    max_completion_tokens=max_output_tokens,
                    extra_body=extra_body,
                )
            except groq.AuthenticationError:
                raise LLMUnavailableError("the AI provider rejected the API key") from None
            except groq.RateLimitError:
                raise LLMUnavailableError(
                    "the AI provider's rate limit was reached; try again in a minute"
                ) from None
            except groq.APIConnectionError:  # includes timeouts
                raise LLMUnavailableError("the AI provider could not be reached") from None
            except groq.BadRequestError:
                problem = "the provider rejected the request (HTTP 400)"
                logger.warning("LLM bad request: schema=%s attempt=%d", schema_name, attempt)
                continue
            except groq.APIStatusError as exc:
                raise LLMUnavailableError(
                    f"the AI provider returned HTTP {exc.status_code}"
                ) from None

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            usage = getattr(response, "usage", None)
            logger.info(
                "LLM call: schema=%s model=%s attempt=%d ms=%d tokens=%s",
                schema_name,
                self.model_name,
                attempt,
                elapsed_ms,
                getattr(usage, "total_tokens", None),
            )

            content = response.choices[0].message.content if response.choices else None
            if not content:
                problem = "empty reply"
                continue
            try:
                return output_model.model_validate_json(content)
            except ValidationError as exc:
                # Log only HOW MANY problems, never the content.
                problem = f"reply did not match the schema ({exc.error_count()} problems)"
                logger.warning("LLM invalid reply: schema=%s attempt=%d", schema_name, attempt)

        raise LLMUnavailableError(f"the AI reply was unusable ({problem})")


@lru_cache
def get_llm_client() -> StructuredLLM | None:
    """The AI client, or None when AI is switched off or no real key is configured."""
    settings = get_settings()
    if not settings.llm_enabled or not settings.groq_configured:
        return None
    return GroqStructuredLLM(settings)