import time
import uuid

from fastapi import APIRouter, Depends, Request
import structlog
from structlog import contextvars

from app.config.settings import get_settings
from app.memory.session_manager import SessionManager
from app.models.request_models import MessageRequest
from app.models.response_models import MessageResponse
from app.services.embedding_service import EmbeddingService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService

settings = get_settings()

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api")


# -----------------------------------------------------------------------
# Dependency providers
# -----------------------------------------------------------------------


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()


def get_prompt_service() -> PromptService:
    return PromptService()


def get_session_manager(request: Request) -> SessionManager:
    return SessionManager(request.app.state.redis_store)


@router.get("/ping")
async def ping() -> dict:
    return {"message": "pong"}


@router.post("/messages", response_model=MessageResponse)
async def messages(
    request: MessageRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    session_manager: SessionManager = Depends(get_session_manager),
) -> MessageResponse:
    start_time = time.perf_counter()
    trace_id = str(uuid.uuid4())

    contextvars.clear_contextvars()
    contextvars.bind_contextvars(
        trace_id=trace_id, employee_name=request.employee_name or "anonymous"
    )

    # 0. Generate a unique Trace ID for this specific interaction

    logger.info("request_started", text=request.text)
    employee_name = request.employee_name or "anonymous"

    # 1. Embed the query and retrieve relevant document chunks
    vector = await embedding_service.embed(request.text)
    chunks = await retrieval_service.search(
        vector, min_score=settings.retrieval_min_score, top_k=settings.vector_top_k
    )
    logger.info("chunks_retrieved", num_chunks=len(chunks), query=request.text)

    # 2. Load conversation history
    history = await session_manager.get_history(employee_name)
    logger.info("session_history_loaded", turns=len(history) // 2)

    # 3. Build the prompt
    messages_list = prompt_service.build_messages(
        query=request.text,
        chunks=chunks,
        history=history,
        employee_name=employee_name,
        company_name=settings.company_name,
    )
    logger.info("prompt_messages", num_messages=len(messages_list))

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info("request_finished", latency_ms=round(duration_ms, 2))

    return MessageResponse(
        status="received",
        trace_id=trace_id,
        duration_ms=round(duration_ms, 2),
        text=request.text,
        embedding_dimensions=len(vector),
        embedding_preview=vector[:5],  # first 5 values as a sanity check
        chunks=[
            {"content": chunk.content, "source": chunk.source, "score": chunk.score}
            for chunk in chunks
        ],
        messages=messages_list,
    )
