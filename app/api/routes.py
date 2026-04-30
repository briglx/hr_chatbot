import time
import uuid

from fastapi import APIRouter, Depends, Request, Path, HTTPException
import structlog
from structlog import contextvars

from app.rag.pipeline import RAGPipeline
from app.memory.session_manager import SessionManager
from app.models.conversations_models import Conversation, ConversationCreate, ConversationItemList, Message, ConversationItemListCreate
from app.services.embedding_service import EmbeddingService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.security.pii_filter import PIIFilter
from app.exceptions.errors import NoDocumentsFoundError, ConversationNotFoundError


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api")


# -----------------------------------------------------------------------
# Dependency providers
# -----------------------------------------------------------------------

def get_session_manager(request: Request) -> SessionManager:
    return SessionManager(request.app.state.redis_store)

def get_rag_pipeline(
    session_manager: SessionManager = Depends(get_session_manager),
) -> RAGPipeline:
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
    return {"message": "pong"}


# -----------------------------------------------------------------------
# Conversation routes
# -----------------------------------------------------------------------

# /api/conversations
@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    body: ConversationCreate,
    conversation_service: ConversationService = Depends(ConversationService),
) -> Conversation:
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.create_conversation(
        metadata=body.metadata,
        messages=body.messages,
    )
    

    return conversation

@router.get("/conversations/{id}", response_model=Conversation)
async def create_conversation(
    id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),
) -> Conversation:
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.get_conversation(id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "message": f"Conversation '{id}' not found"}
        )
    
    return conversation



@router.get("/conversations/{id}/messages", response_model=ConversationItemList)
async def get_conversation_messages(
    id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),
) -> ConversationItemList:
    # conversations = await session_manager.list_conversations()
    conversation = await conversation_service.get_conversation(id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "message": f"Conversation '{id}' not found"}
        )
    
    messages = ConversationItemList(
        object="list",
        data=conversation.messages,
        first_id=conversation.messages[0].id if conversation.messages else None,
        last_id=conversation.messages[-1].id if conversation.messages else None,
        has_more=False,  # TODO: Implement pagination
    )
    
    return messages


@router.get("/conversations/{conversation_id}/messages/{message_id}", response_model=Message)
async def get_conversation_message(
    conversation_id: str = Path(..., description="The conversation ID"),
    message_id: str = Path(..., description="The message ID"),
    conversation_service: ConversationService = Depends(ConversationService),
) -> Message:
    conversation = await conversation_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={"error": "conversation_not_found", "message": f"Conversation '{id}' not found"}
        )
    
    # find matching message
    for message in conversation.messages:
        if message.id == message_id:
            return message
        

    return conversation.messages[0]
    

    
    raise HTTPException(
            status_code=404,
            detail={"error": "message_not_found", "message": f"Message '{id}' not found"}
        )


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationItemList)
async def create_conversation_messages(
    body: ConversationItemListCreate,
    conversation_id: str = Path(..., description="The conversation ID"),
    conversation_service: ConversationService = Depends(ConversationService),
) -> ConversationItemList:
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

    response = ConversationItemList(
        object="list",
        data=conversation.messages,
        first_id=conversation.messages[0].id if conversation.messages else None,
        last_id=conversation.messages[-1].id if conversation.messages else None,
        has_more=False,  # TODO: Implement pagination
    )

    
    return response
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
