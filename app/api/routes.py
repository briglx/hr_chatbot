"""Routes for the FastAPI application, organized by functionality (e.g., conversations, messages, etc.)."""

import time

from fastapi import APIRouter, Depends, HTTPException, Path, Request
import structlog

from app.memory.session_manager import SessionManager
from app.models.conversations_models import (
    Conversation,
    ConversationCreate,
    ConversationItemList,
    ConversationItemListCreate,
    Message,
)
from app.rag.pipeline import RAGPipeline
from app.security.pii_filter import PIIFilter
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api")


# -----------------------------------------------------------------------
# Dependency providers
# -----------------------------------------------------------------------


def get_session_manager(request: Request) -> SessionManager:
    """Provide a SessionManager instance for dependency injection."""
    return SessionManager(request.app.state.redis_store)


def get_rag_pipeline(
    session_manager: SessionManager = Depends(get_session_manager),  # noqa: B008
) -> RAGPipeline:
    """Provide a RAGPipeline instance with all dependencies injected. This includes the LLMService, EmbeddingService, RetrievalService, PromptService, SessionManager, and PIIFilter. The RAGPipeline is the core component that orchestrates the retrieval-augmented generation process for answering user queries."""
    return RAGPipeline(
        llm_service=LLMService(),
        embedding_service=EmbeddingService(),
        retrieval_service=RetrievalService(),
        prompt_service=PromptService(),
        session_manager=session_manager,
        pii_filter=PIIFilter(),
    )


# -----------------------------------------------------------------------
# Health check routes
# -----------------------------------------------------------------------


@router.get("/ping")
async def ping() -> dict:
    """A simple health check endpoint that returns a "pong" message. This can be used to verify that the API is up and running."""
    return {"message": "pong"}


# -----------------------------------------------------------------------
# Conversation routes
# -----------------------------------------------------------------------


# /api/conversations
@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    body: ConversationCreate,
    conversation_service: ConversationService = Depends(ConversationService),  # noqa: B008
) -> Conversation:
    """Create a new conversation with optional metadata and initial messages. The ConversationService is responsible for generating a unique conversation ID, storing the conversation data, and returning the created Conversation object. The response includes the conversation ID, creation timestamp, metadata, and any initial messages provided in the request body."""
    # conversations = await session_manager.list_conversations()

    return await conversation_service.create_conversation(
        metadata=body.metadata,
        messages=body.messages,
    )


@router.get("/conversations/{id}", response_model=Conversation)
async def get_conversation(
    id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),  # noqa: B008
) -> Conversation:
    """Retrieve a conversation by its unique ID. The ConversationService is responsible for fetching the conversation data from storage and returning it as a Conversation object. If the conversation with the specified ID does not exist, a 404 HTTPException is raised with an appropriate error message. The response includes the conversation ID, creation timestamp, metadata, and list of messages associated with the conversation."""
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.get_conversation(id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": f"Conversation '{id}' not found",
            },
        )

    return conversation


@router.get("/conversations/{id}/messages", response_model=ConversationItemList)
async def get_conversation_messages(
    id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),  # noqa: B008
) -> ConversationItemList:
    """Retrieve the list of messages in a conversation by the conversation's unique ID. The ConversationService is responsible for fetching the conversation data from storage and returning the messages as a ConversationItemList object, which includes pagination information such as first_id, last_id, and has_more. If the conversation with the specified ID does not exist, a 404 HTTPException is raised with an appropriate error message. The response includes the list of messages in the conversation along with pagination details."""
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.get_conversation(id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": f"Conversation '{id}' not found",
            },
        )

    return ConversationItemList(
        object="list",
        data=conversation.messages,
        first_id=conversation.messages[0].id if conversation.messages else None,
        last_id=conversation.messages[-1].id if conversation.messages else None,
        has_more=False,  # TODO: Implement pagination
    )


@router.get(
    "/conversations/{conversation_id}/messages/{message_id}", response_model=Message
)
async def get_conversation_message(
    conversation_id: str = Path(..., description="The conversation ID"),
    message_id: str = Path(..., description="The message ID"),
    conversation_service: ConversationService = Depends(ConversationService),  # noqa: B008
) -> Message:
    """Retrieve a specific message from a conversation by the conversation's unique ID and the message's unique ID. The ConversationService is responsible for fetching the conversation data from storage and returning the specified message as a Message object. If the conversation with the specified ID does not exist, a 404 HTTPException is raised with an appropriate error message. If the message with the specified ID does not exist within the conversation, a 404 HTTPException is raised with an appropriate error message. The response includes the message ID, role, content, and creation timestamp."""
    conversation = await conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": f"Conversation '{id}' not found",
            },
        )

    # find matching message
    for message in conversation.messages:
        if message.id == message_id:
            return message

    return conversation.messages[0]

    raise HTTPException(
        status_code=404,
        detail={"error": "message_not_found", "message": f"Message '{id}' not found"},
    )


@router.post(
    "/conversations/{conversation_id}/messages", response_model=ConversationItemList
)
async def create_conversation_messages(
    body: ConversationItemListCreate,
    conversation_id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),  # noqa: B008
) -> ConversationItemList:
    """Append new messages to a conversation by the conversation's unique ID. The ConversationService is responsible for fetching the conversation data from storage, appending the new messages to the conversation, and returning the updated list of messages as a ConversationItemList object, which includes pagination information such as first_id, last_id, and has_more. If the conversation with the specified ID does not exist, a 404 HTTPException is raised with an appropriate error message. The response includes the updated list of messages in the conversation along with pagination details."""
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.get_conversation(conversation_id)

    # TEMP
    if not conversation:
        conversation = Conversation(
            id=id,
            created_at=int(time.time()),
            metadata={"topic": "demo"},
        )

    # TODO: Add new messages to conversation
    for message in body.messages:
        conversation = await conversation_service.append_conversation_message(
            conversation,
            role=message.role,
            content=message.content,
        )

    return ConversationItemList(
        object="list",
        data=conversation.messages,
        first_id=conversation.messages[0].id if conversation.messages else None,
        last_id=conversation.messages[-1].id if conversation.messages else None,
        has_more=False,  # TODO: Implement pagination
    )


# @router.post("/conversations/{conversation_id}/messages", response_model=ChatRequest)
# async def create_conversation(
#     conversation_id: str = Path(..., description="The conversation ID"),
#     body: MessageRequest,
#     conversation_service: ConversationService = Depends(ConversationService),
# ) -> Conversation:
#     # conversations = await session_manager.list_conversations()
#     conversation = await conversation_service.get_conversation(conversation_id)

#     if not conversation:
#         raise HTTPException(
#             status_code=404,
#             detail={"error": "conversation_not_found", "message": f"Conversation '{id}' not found"}
#         )

#     user_message = body.messages[0]

#     return conversation

# @router.post("/messages", response_model=MessageResponse)
# async def messages(
#     request: MessageRequest,
#     pipeline: RAGPipeline = Depends(get_rag_pipeline),
# ) -> MessageResponse:
#     start_time = time.perf_counter()
#     trace_id = str(uuid.uuid4())

#     contextvars.clear_contextvars()
#     contextvars.bind_contextvars(
#         trace_id=trace_id, employee_name=request.employee_name or "anonymous"
#     )

#     logger.info("request_started", text=request.text)


#     try:
#         answer = await pipeline.answer(
#             raw_query=request.text,
#             employee_name=request.employee_name,
#             company_name=request.company_name,
#         )
#     except NoDocumentsFoundError as exc:
#         answer = exc.user_message

#     duration_ms = (time.perf_counter() - start_time) * 1000
#     logger.info("request_finished", latency_ms=round(duration_ms, 2))

#     return MessageResponse(
#         status="ok",
#         text=request.text,
#         answer=answer,
#     )

# start_time = time.perf_counter()
# trace_id = str(uuid.uuid4())

# contextvars.clear_contextvars()
# contextvars.bind_contextvars(
#     trace_id=trace_id, employee_name=request.employee_name or "anonymous"
# )

# logger.info("request_started", text=request.text)
# employee_name = request.employee_name or "anonymous"

# # 1. Embed the query and retrieve relevant document chunks
# vector = await embedding_service.embed(request.text)
# chunks = await retrieval_service.search(
#     vector, min_score=settings.retrieval_min_score, top_k=settings.vector_top_k
# )
# logger.info("chunks_retrieved", num_chunks=len(chunks), query=request.text)

# # 2. Load conversation history
# history = await session_manager.get_history(employee_name)
# logger.info("session_history_loaded", turns=len(history) // 2)

# # 3. Build the prompt
# messages_list = prompt_service.build_messages(
#     query=request.text,
#     chunks=chunks,
#     history=history,
#     employee_name=employee_name,
#     company_name=settings.company_name,
# )
# logger.info("prompt_messages", num_messages=len(messages_list))

# duration_ms = (time.perf_counter() - start_time) * 1000
# logger.info("request_finished", latency_ms=round(duration_ms, 2))

# return MessageResponse(
#     status="received",
#     trace_id=trace_id,
#     duration_ms=round(duration_ms, 2),
#     text=request.text,
#     embedding_dimensions=len(vector),
#     embedding_preview=vector[:5],  # first 5 values as a sanity check
#     chunks=[
#         {"content": chunk.content, "source": chunk.source, "score": chunk.score}
#         for chunk in chunks
#     ],
#     messages=messages_list,
# )
