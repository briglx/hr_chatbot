"""Embedding service — generates vector embeddings via OpenAI.

Used by:
- RAGPipeline: embed the user's query before vector search
- Ingestion pipeline: embed document chunks before storing in the vector DB
- CacheService: embed queries for semantic cache lookups
"""

from __future__ import annotations

from openai import APIStatusError, AsyncAzureOpenAI, RateLimitError
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config.settings import get_settings
from app.exceptions.errors import EmbeddingError, LLMQuotaError

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Generate vector embeddings using the OpenAI embeddings API."""

    def __init__(self) -> None:
        """Initialize the EmbeddingService with OpenAI API client and settings."""
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
    async def embed(self, text: str) -> list[float]:
        """Embed a single string and return the vector.

        Parameters
        ----------
            text: The text to embed (e.g. a user query or document chunk).

        Returns:
        --------
            A list of floats representing the embedding vector.

        Raises:
        -------
            LLMQuotaError: Rate limit hit — retried automatically up to 3 times.
            EmbeddingError: Any other failure from the OpenAI embeddings API.
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        try:
            response = await self._client.embeddings.create(
                model=self._settings.azure_openai_embedding_model,
                input=text.strip(),
                dimensions=self._settings.openai_embedding_dimensions,
            )
        except RateLimitError as exc:
            logger.warning("OpenAI rate limit hit during embedding", error=str(exc))
            raise LLMQuotaError("Embedding rate limit exceeded") from exc
        except APIStatusError as exc:
            logger.error(
                "OpenAI embedding API error", status=exc.status_code, error=str(exc)
            )
            raise EmbeddingError(f"Embedding API error: {exc.status_code}") from exc

        vector = response.data[0].embedding

        logger.debug(
            "Embedding generated",
            model=self._settings.azure_openai_embedding_model,
            dimensions=len(vector),
            tokens_used=response.usage.total_tokens,
        )

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings in a single API call.

        More efficient than calling embed() in a loop for bulk ingestion.

        Parameters:
        -----------
            texts: List of strings to embed. Empty strings are rejected.

        Returns:
        --------
            List of embedding vectors in the same order as the input texts.

        Raises:
        -------
            EmbeddingError: If any text is empty or the API call fails.
        """
        if not texts:
            return []

        clean = [t.strip() for t in texts]
        if any(not t for t in clean):
            raise EmbeddingError("embed_batch received one or more empty strings")

        try:
            response = await self._client.embeddings.create(
                model=self._settings.azure_openai_embedding_model,
                input=clean,
                dimensions=self._settings.openai_embedding_dimensions,
            )
        except RateLimitError as exc:
            raise LLMQuotaError("Embedding rate limit exceeded") from exc
        except APIStatusError as exc:
            raise EmbeddingError(f"Embedding API error: {exc.status_code}") from exc

        # OpenAI returns embeddings in the same order as input
        vectors = [
            item.embedding for item in sorted(response.data, key=lambda x: x.index)
        ]

        logger.info(
            "Batch embedding complete",
            count=len(vectors),
            tokens_used=response.usage.total_tokens,
        )

        return vectors
