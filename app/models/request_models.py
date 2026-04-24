from pydantic import BaseModel, Field
from typing import Any

class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The user's message text")
    employee_name: str = Field(None, description="The employee's name (optional)")

class InputMessage(BaseModel):
    role: str = Field(..., description="The role of the message sender (e.g., 'user', 'assistant', 'system')")
    content: str = Field(..., description="The content of the message")

class MessageItem(BaseModel):
    type: str = "message"
    role: str
    content: str

class CreateConversationRequest(BaseModel):
    metadata: dict[str, Any] = {},
    items: list[MessageItem] = []