"""Session manager — tracks multi-turn conversation context per Teams user.

Each session stores an ordered list of (role, content) message turns that
is prepended to every LLM call, giving the bot conversation memory.
The history is capped at `max_turns` to stay within the model's context window.
"""

from __future__ import annotations

import json
from typing import TypedDict

import structlog

from app.config.settings import get_settings
from app.exceptions.errors import SessionError, SessionStoreUnavailableError
from app.memory.stores.redis_store import RedisStore

logger = structlog.get_logger(__name__)


class Message(TypedDict):
    """A single message in the conversation history."""

    role: str  # "user" | "assistant" | "system"
    content: str


class SessionManager:
    """Manages per-user conversation sessions backed by Redis."""

    def __init__(self, redis_store: RedisStore) -> None:
        """Initialize the SessionManager with a RedisStore instance."""
        self._store = redis_store
        self._settings = get_settings()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_history(self, user_id: str) -> list[Message]:
        """Return the stored conversation history for a user.

        Returns an empty list if no session exists yet.
        """
        key = self._key(user_id)
        try:
            raw = await self._store.get(key)
            if raw is None:
                return []
            return json.loads(raw)
        except Exception as exc:
            logger.error("Failed to read session", user_id=user_id, error=str(exc))
            raise SessionStoreUnavailableError(
                f"Could not load session for user {user_id}"
            ) from exc

    async def append_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Append a user/assistant turn pair and trim history to max_turns."""
        history = await self.get_history(user_id)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_message})

        # Keep only the most recent N turns (each turn = 2 messages)
        max_messages = self._settings.max_conversation_turns * 2
        if len(history) > max_messages:
            history = history[-max_messages:]

        await self._save(user_id, history)
        logger.debug(
            "Session updated",
            user_id=user_id,
            turns=len(history) // 2,
        )

    async def clear_session(self, user_id: str) -> None:
        """Delete a user's conversation history."""
        key = self._key(user_id)
        try:
            await self._store.delete(key)
            logger.info("Session cleared", user_id=user_id)
        except Exception as exc:
            raise SessionError(f"Could not clear session for user {user_id}") from exc

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _save(self, user_id: str, history: list[Message]) -> None:
        key = self._key(user_id)
        try:
            await self._store.set(
                key,
                json.dumps(history),
                ttl=self._settings.session_ttl_seconds,
            )
        except Exception as exc:
            raise SessionStoreUnavailableError(
                f"Could not save session for user {user_id}"
            ) from exc

    @staticmethod
    def _key(user_id: str) -> str:
        return f"session:{user_id}"
