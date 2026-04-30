"""LLM service — sends a message list to Azure OpenAI and returns the response.

This service only handles the API call itself. It does not build prompts
or know anything about HR documents — that is PromptService's job.
"""

from __future__ import annotations

from openai import APIStatusError, AsyncAzureOpenAI, BadRequestError, RateLimitError
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config.settings import get_settings
from app.exceptions.errors import (
    LLMContentPolicyError,
    LLMContextLengthError,
    LLMError,
    LLMQuotaError,
)
from app.memory.session_manager import Message

logger = structlog.get_logger(__name__)


class LLMService:
    """Async wrapper for Azure OpenAI chat completions."""

    def __init__(self) -> None:
        """Initialize the LLMService with an AsyncAzureOpenAI client using settings from the configuration. The client is used to make API calls to Azure OpenAI for generating embeddings and chat completions."""
        self._settings = get_settings()
        self._client = AsyncAzureOpenAI(
            api_key=self._settings.azure_openai_api_key,
            azure_endpoint=self._settings.azure_openai_endpoint,
            api_version=self._settings.azure_openai_api_version,
        )

    @retry(
        retry=retry_if_exception_type(LLMQuotaError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        user_id: str | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Parameters:
        -----------
            messages: Full message list from PromptService.build_messages().
            temperature: Override the default temperature from settings.
            max_tokens: Override the default max_tokens from settings.
            user_id: Passed to Azure OpenAI for abuse detection.

        Returns:
        --------
            The assistant's response text.

        Raises:
        -------
            LLMQuotaError: Rate limit exceeded — retried automatically up to 3 times.
            LLMContextLengthError: Prompt exceeds the model's context window.
            LLMContentPolicyError: Request blocked by content policy.
            LLMError: Any other Azure OpenAI API error.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.azure_openai_completion_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature
                if temperature is not None
                else self._settings.openai_temperature,
                max_tokens=max_tokens or self._settings.openai_max_tokens,
                user=user_id,
            )
        except RateLimitError as exc:
            logger.warning("Azure OpenAI rate limit hit", error=str(exc))
            raise LLMQuotaError("Rate limit exceeded") from exc
        except BadRequestError as exc:
            if "context_length_exceeded" in str(exc):
                raise LLMContextLengthError("Prompt exceeded context window") from exc
            if "content_filter" in str(exc):
                raise LLMContentPolicyError("Content policy violation") from exc
            raise LLMError(f"Bad request: {exc}") from exc
        except APIStatusError as exc:
            logger.error(
                "Azure OpenAI API error", status=exc.status_code, error=str(exc)
            )
            raise LLMError(f"API error: {exc.status_code}") from exc

        content = response.choices[0].message.content or ""

        logger.info(
            "LLM response received",
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        return content.strip()
