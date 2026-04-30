from pydantic import BaseModel, Field
from typing import Any, Optional

# class ChunkResult(BaseModel):
#     content: str
#     source: str
#     score: float


# class MessageResponse(BaseModel):
#     status: str
#     trace_id: str
#     duration_ms: float
#     text: str
#     embedding_dimensions: int
#     embedding_preview: list[float]
#     chunks: list[ChunkResult]
#     messages: list[dict]

class MessageCreate(BaseModel):
    type: str = "message"
    role: str
    content: str
    
class Message(BaseModel):
    id: Optional[str] = Field(..., description="The unique ID of the message")
    type: str = "message"
    role: str
    content: str
    create_time: int = Field(..., description="The time at which the message was created, measured in seconds since the Unix epoch.")
    

class ConversationItemListCreate(BaseModel):
    messages: list[MessageCreate]

class ConversationItemList(BaseModel):
    object: str = "list"
    data: list[Message]
    first_id: str
    last_id: str
    has_more: bool

class ConversationCreate(BaseModel):
    metadata: dict[str, Any] = {},
    messages: list[MessageCreate] = []
    context: Optional[dict] = None
    client: Optional[dict] = None

class Conversation(BaseModel):
    id: str
    object: str = "conversation"
    create_time: int = Field(..., description="The time at which the message was created, measured in seconds since the Unix epoch.")
    metadata: dict[str, Any] = {},
    messages: list[Message]

