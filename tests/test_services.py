from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions.errors import EmbeddingError, LLMQuotaError, VectorStoreError
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import DocumentChunk, RetrievalService

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

FAKE_VECTOR = [0.1] * 1536


class TestEmbeddingService:
    def make_embedding_response(
        self, vectors: list[list[float]], total_tokens: int = 10
    ):
        """Build a fake OpenAI embeddings response."""
        response = MagicMock()
        response.data = [
            MagicMock(embedding=vector, index=i) for i, vector in enumerate(vectors)
        ]
        response.usage.total_tokens = total_tokens
        return response

    FAKE_VECTOR = [0.1] * 1536

    # -----------------------------------------------------------------------
    # embed()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_embed_returns_vector(self):
        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=self.make_embedding_response([self.FAKE_VECTOR])
            )
            svc = EmbeddingService()
            result = await svc.embed("How many vacation days do I get?")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert result == self.FAKE_VECTOR

    @pytest.mark.asyncio
    async def test_embed_calls_correct_model(self):
        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            create_mock = AsyncMock(
                return_value=self.make_embedding_response([self.FAKE_VECTOR])
            )
            mock_openai.return_value.embeddings.create = create_mock

            svc = EmbeddingService()
            await svc.embed("test query")

            call_kwargs = create_mock.call_args.kwargs
            assert call_kwargs["input"] == "test query"
            assert "model" in call_kwargs

    @pytest.mark.asyncio
    async def test_embed_strips_whitespace(self):
        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            create_mock = AsyncMock(
                return_value=self.make_embedding_response([self.FAKE_VECTOR])
            )
            mock_openai.return_value.embeddings.create = create_mock

            svc = EmbeddingService()
            await svc.embed("  padded query  ")

            call_kwargs = create_mock.call_args.kwargs
            assert call_kwargs["input"] == "padded query"

    @pytest.mark.asyncio
    async def test_embed_raises_on_empty_string(self):
        svc = EmbeddingService()
        with pytest.raises(EmbeddingError, match="empty"):
            await svc.embed("")

    @pytest.mark.asyncio
    async def test_embed_raises_on_whitespace_only(self):
        svc = EmbeddingService()
        with pytest.raises(EmbeddingError, match="empty"):
            await svc.embed("   ")

    @pytest.mark.asyncio
    async def test_embed_raises_quota_error_on_rate_limit(self):
        from openai import RateLimitError

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                side_effect=RateLimitError(
                    message="rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={},
                )
            )
            svc = EmbeddingService()
            with pytest.raises(LLMQuotaError):
                await svc.embed("test query")

    @pytest.mark.asyncio
    async def test_embed_raises_embedding_error_on_api_failure(self):
        from openai import APIStatusError

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                side_effect=APIStatusError(
                    message="internal server error",
                    response=MagicMock(status_code=500),
                    body={},
                )
            )
            svc = EmbeddingService()
            with pytest.raises(EmbeddingError):
                await svc.embed("test query")

    # -----------------------------------------------------------------------
    # embed_batch()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_embed_batch_returns_multiple_vectors(self):
        vectors = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=self.make_embedding_response(vectors)
            )
            svc = EmbeddingService()
            result = await svc.embed_batch(["query one", "query two", "query three"])

        assert len(result) == 3
        assert result[0] == vectors[0]
        assert result[1] == vectors[1]
        assert result[2] == vectors[2]

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list_returns_empty(self):
        svc = EmbeddingService()
        result = await svc.embed_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_batch_raises_on_empty_string_in_list(self):
        svc = EmbeddingService()
        with pytest.raises(EmbeddingError, match="empty"):
            await svc.embed_batch(["valid text", "", "more text"])

    @pytest.mark.asyncio
    async def test_embed_batch_raises_quota_error_on_rate_limit(self):
        from openai import RateLimitError

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                side_effect=RateLimitError(
                    message="rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body={},
                )
            )
            svc = EmbeddingService()
            with pytest.raises(LLMQuotaError, match="rate limit"):
                await svc.embed_batch(["query one", "query two"])

    @pytest.mark.asyncio
    async def test_embed_batch_raises_embedding_error_on_api_failure(self):
        from openai import APIStatusError

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                side_effect=APIStatusError(
                    message="internal server error",
                    response=MagicMock(status_code=500),
                    body={},
                )
            )
            svc = EmbeddingService()
            with pytest.raises(EmbeddingError, match="Embedding API error: 500"):
                await svc.embed_batch(["query one", "query two"])

    @pytest.mark.asyncio
    async def test_embed_batch_preserves_order(self):
        """OpenAI may return embeddings out of order — verify we sort by index."""
        v1, v2, v3 = [0.1] * 1536, [0.2] * 1536, [0.3] * 1536

        response = MagicMock()
        # Return in reverse order to test sorting
        response.data = [
            MagicMock(embedding=v3, index=2),
            MagicMock(embedding=v1, index=0),
            MagicMock(embedding=v2, index=1),
        ]
        response.usage.total_tokens = 30

        with patch("app.services.embedding_service.AsyncAzureOpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=response
            )
            svc = EmbeddingService()
            result = await svc.embed_batch(["a", "b", "c"])

        assert result[0] == v1
        assert result[1] == v2
        assert result[2] == v3


class TestRetrievalService:
    def make_row(
        self,
        id=1,
        content="You get 20 vacation days per year.",
        source="hr-policy.pdf",
        score=0.92,
        metadata=None,
    ):
        """Build a fake SQLAlchemy result row."""
        row = MagicMock()
        row.id = id
        row.content = content
        row.source = source
        row.score = score
        row.metadata = metadata or {}
        return row

    @pytest.fixture
    def mock_session(self):
        """Patch create_async_engine and sessionmaker so no real DB is needed."""
        session = AsyncMock()
        session_factory = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=session),
                __aexit__=AsyncMock(return_value=False),
            )
        )

        with (
            patch("app.services.retrieval_service.create_async_engine"),
            patch(
                "app.services.retrieval_service.sessionmaker",
                return_value=session_factory,
            ),
        ):
            yield session

    # -----------------------------------------------------------------------
    # search() — happy path
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_search_returns_document_chunks(self, mock_session):
        rows = [self.make_row(id=1, score=0.92), self.make_row(id=2, score=0.85)]
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=rows))
        )

        svc = RetrievalService()
        results = await svc.search(FAKE_VECTOR)

        assert len(results) == 2
        assert all(isinstance(r, DocumentChunk) for r in results)

    @pytest.mark.asyncio
    async def test_search_maps_fields_correctly(self, mock_session):
        row = self.make_row(
            id=42,
            content="You get 20 vacation days.",
            source="hr-policy.pdf",
            score=0.91,
            metadata={"page": 3},
        )
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[row]))
        )

        svc = RetrievalService()
        results = await svc.search(FAKE_VECTOR)
        chunk = results[0]

        assert chunk.id == 42
        assert chunk.content == "You get 20 vacation days."
        assert chunk.source == "hr-policy.pdf"
        assert chunk.score == 0.91
        assert chunk.metadata == {"page": 3}

    @pytest.mark.asyncio
    async def test_search_rounds_score_to_4_decimal_places(self, mock_session):
        row = self.make_row(score=0.912345678)
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[row]))
        )

        svc = RetrievalService()
        results = await svc.search(FAKE_VECTOR)

        assert results[0].score == 0.9123

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_results(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )

        svc = RetrievalService()
        results = await svc.search(FAKE_VECTOR)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_uses_default_top_k(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )

        svc = RetrievalService()
        await svc.search(FAKE_VECTOR)

        call_params = mock_session.execute.call_args[0][1]
        assert call_params["top_k"] == 5  # matches make_settings().vector_top_k

    @pytest.mark.asyncio
    async def test_search_respects_custom_top_k(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )

        svc = RetrievalService()
        await svc.search(FAKE_VECTOR, top_k=3)

        call_params = mock_session.execute.call_args[0][1]
        assert call_params["top_k"] == 3

    @pytest.mark.asyncio
    async def test_search_passes_min_score(self, mock_session):
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )

        svc = RetrievalService()
        await svc.search(FAKE_VECTOR, min_score=0.75)

        call_params = mock_session.execute.call_args[0][1]
        assert call_params["min_score"] == 0.75

    @pytest.mark.asyncio
    async def test_search_handles_none_metadata(self, mock_session):
        row = self.make_row(metadata=None)
        mock_session.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[row]))
        )

        svc = RetrievalService()
        results = await svc.search(FAKE_VECTOR)

        assert results[0].metadata == {}

    # -----------------------------------------------------------------------
    # search() — error handling
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_search_raises_vector_store_error_on_db_failure(self, mock_session):
        mock_session.execute = AsyncMock(side_effect=Exception("connection refused"))

        svc = RetrievalService()
        with pytest.raises(VectorStoreError, match="Failed to query the vector store"):
            await svc.search(FAKE_VECTOR)

    @pytest.mark.asyncio
    async def test_search_wraps_original_exception(self, mock_session):
        original = Exception("timeout")
        mock_session.execute = AsyncMock(side_effect=original)

        svc = RetrievalService()
        with pytest.raises(VectorStoreError) as exc_info:
            await svc.search(FAKE_VECTOR)

        assert exc_info.value.__cause__ is original

    # -----------------------------------------------------------------------
    # close()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self):
        with (
            patch("app.services.retrieval_service.create_async_engine") as mock_engine,
            patch("app.services.retrieval_service.sessionmaker"),
        ):
            mock_engine.return_value.dispose = AsyncMock()

            svc = RetrievalService()
            await svc.close()

            mock_engine.return_value.dispose.assert_called_once()
