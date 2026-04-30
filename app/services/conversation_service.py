"""Conversation Service - Manage conversations and conversation items."""

import secrets
import time
from typing import Any

from app.models.conversations_models import Conversation, Message, MessageCreate


class ConversationService:
    """Service for managing conversations and conversation items.

    This is a placeholder implementation that generates unique IDs and
    timestamps, but does not persist data. In a real implementation,
    this would interface with a database or cache to store and retrieve
    conversations and messages.
    """

    def __init__(self):
        """Initialize the ConversationService. In a real implementation, this might set up database connections or in-memory caches."""
        pass

    def get_timestamp(self) -> int:
        """Get the current timestamp in seconds since the Unix epoch."""
        return int(time.time())

    def get_hex_timestamp(self) -> int:
        """Get the current timestamp in hexadecimal format, which can be used as part of unique ID generation."""
        return format(self.get_timestamp(), "x")

    def generate_id(self, prefix: str) -> str:
        """Generate a unique ID with a given prefix using a combination of timestamp and random hex string."""
        timestamp = self.get_hex_timestamp()
        random_part = secrets.token_hex(20)  # 40 random hex chars
        return f"{prefix}_{timestamp}{random_part}"

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID using a combination of a prefix, timestamp, and random hex string."""
        prefix = "conv"
        return self.generate_id(prefix)

    def generate_message_id(self) -> str:
        """Generate a unique message ID using a combination of a prefix, timestamp, and random hex string."""
        prefix = "msg"
        return self.generate_id(prefix)

    async def create_conversation(
        self,
        metadata: dict[str, Any],
        messages: list[MessageCreate] | None = None,
    ) -> Conversation:
        """Create a new conversation with a unique ID and metadata."""
        conversation_id = self.generate_conversation_id()

        new_conversation = Conversation(
            id=conversation_id,
            create_time=self.get_timestamp(),
            metadata=metadata,
            # Convert MessageCreate to Message by adding an ID (could also be done in the API layer)
            messages=[
                Message(
                    id=self.generate_message_id(),
                    role=msg.role,
                    content=msg.content,
                    create_time=self.get_timestamp(),
                )
                for msg in messages
            ],
        )

        # TODO: Get response from LLM
        if messages and messages[-1].role == "user":
            assistant_message = Message(
                id=self.generate_message_id(),
                role="assistant",
                content="Hmmm, I don't have a good answer for that.",
                create_time=self.get_timestamp(),
            )
            new_conversation.messages.append(assistant_message)

            # TODO: Generate a Conversation Title
            new_conversation.metadata["title"] = "Demo Conversation"

        return new_conversation

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Retrieve a conversation by its ID."""
        # Placeholder implementation - in a real implementation, this would query a database or cache

        return Conversation(
            id=conversation_id,
            create_time=self.get_timestamp(),
            metadata={
                "title": "Life and it's Meaning",
                "topic": "demo",
            },
            messages=[
                Message(
                    id=self.generate_message_id(),
                    role="user",
                    content="What is the meaning of life?",
                    create_time=self.get_timestamp(),
                ),
                Message(
                    id=self.generate_message_id(),
                    role="assistant",
                    content="Some say it's 42.",
                    create_time=self.get_timestamp(),
                ),
                Message(
                    id=self.generate_message_id(),
                    role="user",
                    content="No, that's not right. Can you try again?",
                    create_time=self.get_timestamp(),
                ),
                Message(
                    id=self.generate_message_id(),
                    role="assistant",
                    content="Okay, how about this: The meaning of life is to find your own meaning.",
                    create_time=self.get_timestamp(),
                ),
            ],
        )

    async def append_conversation_message(
        self, conversation: Conversation, role: str, content: str
    ):
        """Append a message to an existing conversation."""
        # Placeholder implementation - in a real implementation, this would update a database or cache

        conversation.messages.append(
            Message(
                id=self.generate_message_id(),
                role=role,
                content=content,
                create_time=self.get_timestamp(),
            )
        )
        return conversation

    # async def get_history(self, conversation_id: str) -> list[Message]:
    #     """Retrieve the message history for a given conversation ID. This method first checks an in-memory cache for the conversation's messages. If the conversation is not found in the cache, it performs a cold load from the database and populates the cache with the retrieved messages before returning them."""
    #     if conversation_id in self._cache:
    #         return self._cache[conversation_id]  # fast path

    #     # cold load from DB, populate cache
    #     messages = await db.fetch_messages(conversation_id)
    #     self._cache[conversation_id] = messages
    #     return messages

    # async def append_message(self, conversation_id: str, message: Message):
    #     # write to both
    #     self._cache.setdefault(conversation_id, []).append(message)
    #     await db.insert_message(conversation_id, message)
