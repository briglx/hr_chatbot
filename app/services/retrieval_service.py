"""Retrieval service — searches the pgvector database for relevant document chunks.

Takes a query vector (produced by EmbeddingService) and returns the top-k
most semantically similar chunks from the HR knowledge base.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import structlog

from app.config.settings import get_settings
from app.exceptions.errors import VectorStoreError

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    """A retrieved document chunk returned from the vector store."""

    id: int
    content: str
    source: str
    score: float  # cosine similarity score — higher is more relevant
    metadata: dict


class RetrievalService:
    """Search pgvector for document chunks similar to a query vector."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._engine: AsyncEngine = create_async_engine(
            self._settings.database_url,
            echo=self._settings.is_development,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def search(
        self,
        query_vector: list[float],
        top_k: int | None = None,
        *,
        min_score: float = 0.5,
    ) -> list[DocumentChunk]:
        """Find the most relevant document chunks for a query vector.

        Args:
            query_vector: Embedding vector for the user's query.
            top_k: Number of chunks to return. Defaults to settings.vector_top_k.
            min_score: Minimum cosine similarity score (0-1). Chunks below this
                       threshold are excluded even if they are in the top-k.
                       Defaults to settings.retrieval_min_score.

        Returns:
            List of DocumentChunk ordered by relevance (highest score first).

        Raises:
            VectorStoreError: If the database query fails.
        """
        k = top_k or self._settings.vector_top_k

        # pgvector uses <=> for cosine distance (0 = identical, 2 = opposite)
        # Convert to similarity score: similarity = 1 - distance
        sql = text("""
            SELECT
                id,
                content,
                source,
                metadata,
                1 - (embedding <=> CAST(:query_vector AS vector)) AS score
            FROM documents
            WHERE 1 - (embedding <=> CAST(:query_vector AS vector)) >= :min_score
            ORDER BY score DESC
            LIMIT :top_k
        """)

        logger.info(
            "query_vector received for search",
            vector_length=len(query_vector),
            top_k=k,
            min_score=min_score,
        )

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    sql,
                    {
                        "query_vector": str(query_vector),
                        "min_score": min_score,
                        "top_k": k,
                    },
                )
                rows = result.fetchall()
        except Exception as exc:
            logger.error("Vector search failed", error=str(exc))
            raise VectorStoreError("Failed to query the vector store") from exc

        chunks = [
            DocumentChunk(
                id=row.id,
                content=row.content,
                source=row.source,
                score=round(float(row.score), 4),
                metadata=row.metadata or {},
            )
            for row in rows
        ]

        logger.info(
            "Vector search complete",
            top_k=k,
            results_returned=len(chunks),
            top_score=chunks[0].score if chunks else None,
        )

        return chunks

    async def close(self) -> None:
        """Dispose the connection pool — call during app shutdown."""
        await self._engine.dispose()
