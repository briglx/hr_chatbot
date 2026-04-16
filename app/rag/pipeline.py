"""RAG pipeline — orchestrates the full query → answer flow.

Steps:
1. PII filter on the incoming query
2. Embed the query
3. Retrieve relevant document chunks
4. Load conversation history
5. Build the prompt
6. Call the LLM
7. Save the turn to session history
8. Return the answer
"""

from __future__ import annotations

import time

import structlog

from app.config.settings import get_settings
from app.exceptions.errors import NoDocumentsFoundError
from app.memory.session_manager import SessionManager
from app.security.pii_filter import PIIFilter
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline."""

    def __init__(
        self,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        prompt_service: PromptService,
        session_manager: SessionManager,
        pii_filter: PIIFilter,
    ) -> None:
        self._llm = llm_service
        self._embedder = embedding_service
        self._retriever = retrieval_service
        self._prompter = prompt_service
        self._sessions = session_manager
        self._pii = pii_filter
        self._settings = get_settings()

    async def answer(
        self,
        raw_query: str,
        *,
        employee_name: str | None = None,
        company_name: str | None = None,
        min_score: float = 0.4,
    ) -> str:
        """Process a user query and return the bot's answer.

        Args:
            raw_query: The raw message text from the user.
            employee_name: Optional — passed to prompt for personalisation.
            company_name: Optional — passed to prompt for personalisation.
            min_score: Minimum cosine similarity score for retrieved chunks.

        Returns:
            The assistant's answer string.

        Raises:
            NoDocumentsFoundError: No relevant HR documents found.
            LLMError: LLM call failed.
        """
        start = time.perf_counter()

        # 1. PII filter — redact before any external call
        clean_query = self._pii.redact(raw_query)

        # 2. Embed the query
        query_vector = await self._embedder.embed(clean_query)

        # 3. Retrieve relevant document chunks
        chunks = await self._retriever.search(
            query_vector,
            top_k=self._settings.vector_top_k,
            min_score=min_score,
        )

        if not chunks:
            raise NoDocumentsFoundError(
                "No relevant HR documents found",
                context={"employee_name": employee_name, "query": clean_query},
            )

        logger.info("Chunks retrieved", num_chunks=len(chunks), employee_name=employee_name)

        # 4. Load conversation history
        history = await self._sessions.get_history(employee_name)

        # 5. Build the prompt
        messages = self._prompter.build_messages(
            query=clean_query,
            chunks=chunks,
            history=history,
            employee_name=employee_name,
            company_name=company_name,
        )

        # 6. Call the LLM
        answer = await self._llm.complete(messages, user_id=employee_name)

        # 7. Save the turn to session history
        await self._sessions.append_turn(
            employee_name=employee_name,
            user_message=clean_query,
            assistant_message=answer,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "RAG pipeline complete",
            employee_name=employee_name,
            chunks_retrieved=len(chunks),
            latency_ms=round(elapsed * 1000),
        )

        return answer