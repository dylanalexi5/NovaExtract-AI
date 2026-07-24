"""
Instructor-patched OpenAI client for structured LLM extraction.

Uses the `instructor` library to patch the official OpenAI client,
enabling validated Pydantic model responses directly from the LLM.
Supports any OpenAI-compatible provider (OpenAI, Groq, Azure, Ollama)
via configurable base_url.

Key design decisions:
- Async client for non-blocking FastAPI integration.
- Explicit timeout and retry configuration for production resilience.
- Domain exception mapping for clean error propagation to use cases.
"""

from __future__ import annotations

import logging
from typing import TypeVar

import instructor
import openai
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.domain.exceptions import (
    LLMExtractionError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── System Prompt ────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert data extraction assistant specialized in parsing CVs and resumes. "
    "Your task is to extract structured information from the provided document text. "
    "The text may contain PII placeholders like <PERSON>, <EMAIL_ADDRESS>, <PHONE_NUMBER> — "
    "preserve these placeholders exactly as-is in your output. "
    "Extract all available information accurately. For fields not found in the text, "
    "use null or empty lists as appropriate. "
    "Evaluate your overall extraction confidence from 0.0 (no useful data) to 1.0 (complete profile)."
)


class AIExtractor:
    """
    LLM-powered structured data extractor using instructor + OpenAI client.

    Patches the AsyncOpenAI client with instructor to enforce Pydantic model
    validation on LLM responses. Supports OpenAI, Groq, and any
    OpenAI-compatible API via base_url configuration.
    """

    def __init__(
        self,
        settings: Settings,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        """
        Initializes the instructor-patched async OpenAI client.

        Args:
            settings: Application settings containing API keys and model config.
            timeout_seconds: Maximum wait time per LLM request.
            max_retries: Number of retries on transient failures (instructor handles retries
                         for validation errors; this covers network-level retries).
        """
        self._model = settings.OPENAI_MODEL
        self._timeout = timeout_seconds
        self._provider_name = settings.OPENAI_BASE_URL or "openai"

        # Build base OpenAI async client
        base_client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

        # Patch with instructor for structured output enforcement
        self._client = instructor.from_openai(base_client)

        logger.info(
            "AIExtractor initialized. Model: %s, Provider: %s, Timeout: %.1fs",
            self._model,
            self._provider_name,
            self._timeout,
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((LLMRateLimitError, LLMTimeoutError)),
        reraise=True,
    )
    async def extract(
        self,
        text: str,
        response_model: type[T],
        system_prompt: str = EXTRACTION_SYSTEM_PROMPT,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> T:
        """
        Sends sanitized text to the LLM and returns a validated Pydantic model instance.

        The response_model's Field descriptions are automatically injected by instructor
        as extraction instructions in the LLM prompt, enabling schema-driven prompt engineering.

        Args:
            text: Sanitized document text (PII already anonymized).
            response_model: Target Pydantic model class for structured output.
            system_prompt: System-level instructions for the LLM.
            temperature: Sampling temperature (0.0 for deterministic extraction).
            max_retries: Instructor-level retries for validation failures
                         (re-prompts the LLM on schema violations).

        Returns:
            Validated instance of response_model populated with extracted data.

        Raises:
            LLMTimeoutError: If the request exceeds timeout_seconds.
            LLMRateLimitError: If the provider returns HTTP 429.
            LLMExtractionError: For any other LLM processing failure.
        """
        logger.info(
            "Starting LLM extraction. Model: %s, Schema: %s, Text length: %d chars",
            self._model,
            response_model.__name__,
            len(text),
        )

        try:
            result = await self._client.chat.completions.create(
                model=self._model,
                response_model=response_model,
                max_retries=max_retries,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )

            logger.info(
                "LLM extraction completed. Schema: %s",
                response_model.__name__,
            )
            return result

        except openai.APITimeoutError as exc:
            logger.error("LLM request timed out after %.1fs: %s", self._timeout, exc)
            raise LLMTimeoutError(self._timeout) from exc

        except openai.RateLimitError as exc:
            logger.error("LLM rate limit hit for provider '%s': %s", self._provider_name, exc)
            raise LLMRateLimitError(self._provider_name) from exc

        except openai.APIConnectionError as exc:
            logger.error("Failed to connect to LLM provider '%s': %s", self._provider_name, exc)
            raise LLMExtractionError(
                f"Connection failed to provider '{self._provider_name}': {exc}"
            ) from exc

        except openai.APIStatusError as exc:
            logger.error("LLM API error (status %d): %s", exc.status_code, exc.message)
            raise LLMExtractionError(
                f"API error from provider (HTTP {exc.status_code}): {exc.message}"
            ) from exc

        except Exception as exc:
            logger.error("Unexpected LLM extraction error: %s", exc)
            raise LLMExtractionError(f"Unexpected extraction failure: {exc}") from exc
