from fastapi import APIRouter, Depends

from app.models.request_models import MessageRequest
from app.models.response_models import MessageResponse
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
import structlog

logger = structlog.get_logger(__name__)


router = APIRouter(prefix="/api")



def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

def get_retrieval_service() -> RetrievalService:
    return RetrievalService()

@router.get("/ping")
async def ping() -> dict:
    return {"message": "pong"}


@router.post("/messages", response_model=MessageResponse)
async def messages(
    request: MessageRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> MessageResponse:
    vector = await embedding_service.embed(request.text)
    chunks = await retrieval_service.search(vector, min_score=0.4)

    logger.info("Chunks retrieved", num_chunks=len(chunks), query=request.text)

    return MessageResponse(
        status="received",
        text=request.text,
        embedding_dimensions=len(vector),
        embedding_preview=vector[:5],  # first 5 values as a sanity check
        chunks=[
            {"content": chunk.content, "source": chunk.source, "score": chunk.score}
            for chunk in chunks
        ],
    )
