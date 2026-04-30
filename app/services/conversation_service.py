"""Conversation Service - Manage conversations and conversation items."""
import secrets
import time
from app.models.response_models import Conversation
from app.models.request_models import MessageItem
from typing import Any

class ConversationService:
    def __init__(self):
        pass

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID using a combination of a prefix, timestamp, and random hex string."""
        prefix = "conv"
        timestamp = format(int(time.time()), 'x')  # hex timestamp
        random_part = secrets.token_hex(20)         # 40 random hex chars
        return f"{prefix}_{timestamp}{random_part}"
    
    async def create_conversation(
        self,
        metadata: dict[str, Any] = {},
        items: list[MessageItem] = [],
    ) -> Conversation:
        """Create a new conversation with a unique ID and metadata."""
        conversation_id = self.generate_conversation_id()

        new_conversation = Conversation(
            id=conversation_id,
            created_at=int(time.time()),
            metadata=metadata,
        )
        
        return new_conversation
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Retrieve a conversation by its ID."""
        # Placeholder implementation - in a real implementation, this would query a database or cache
        return None
        return Conversation(
            id=conversation_id,
            created_at=int(time.time()),
            metadata={},
        )
    

    async def get_history(self, conversation_id: str) -> list[Message]:
        if conversation_id in self._cache:
            return self._cache[conversation_id]  # fast path

        # cold load from DB, populate cache
        messages = await db.fetch_messages(conversation_id)
        self._cache[conversation_id] = messages
        return messages

    async def append_message(self, conversation_id: str, message: Message):
        # write to both
        self._cache.setdefault(conversation_id, []).append(message)
        await db.insert_message(conversation_id, message)