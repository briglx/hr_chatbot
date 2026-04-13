class HRBotError(Exception):
    """Base class for all HR chatbot application errors."""

    http_status: int = 500
    user_message: str = "Something went wrong. Please try again."

    def __init__(
        self,
        message: str,
        *,
        context: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.context: dict = context or {}


# ------------------------------------------------------------------ #
# LLM / OpenAI errors
# ------------------------------------------------------------------ #

class LLMError(HRBotError):
    """Base class for errors originating from the LLM service."""
    user_message = "I'm having trouble generating a response right now. Please try again."


class LLMQuotaError(LLMError):
    """OpenAI rate limit or quota exceeded."""
    http_status = 429
    user_message = "I'm receiving a lot of requests right now. Please wait a moment and try again."


# ------------------------------------------------------------------ #
# Retrieval / RAG errors
# ------------------------------------------------------------------ #

class RetrievalError(HRBotError):
    """Base class for errors in the retrieval pipeline."""
    user_message = "I couldn't search the HR knowledge base right now. Please try again."


class EmbeddingError(RetrievalError):
    """Failed to generate embeddings for a query or document."""

class VectorStoreError(RetrievalError):
    """Failed to connect to or query the vector database."""
