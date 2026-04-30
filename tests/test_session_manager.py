import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions.errors import SessionError, SessionStoreUnavailableError
from app.memory.session_manager import Message, SessionManager
from app.memory.stores.redis_store import RedisStore

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def make_settings():
    settings = MagicMock()
    settings.session_ttl_seconds = 3600
    settings.max_conversation_turns = 3
    return settings


def make_redis_store() -> AsyncMock:
    store = AsyncMock(spec=RedisStore)
    store.get = AsyncMock(return_value=None)
    store.set = AsyncMock()
    store.delete = AsyncMock()
    return store


def make_history(turns: int = 2) -> list[Message]:
    history = []
    for i in range(turns):
        history.append({"role": "user", "content": f"user message {i}"})
        history.append({"role": "assistant", "content": f"assistant message {i}"})
    return history


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------


class TestSessionManager:
    @pytest.fixture(autouse=True)
    def mock_settings(self):
        with patch(
            "app.memory.session_manager.get_settings", return_value=make_settings()
        ):
            yield

    @pytest.fixture
    def redis_store(self) -> AsyncMock:
        return make_redis_store()

    @pytest.fixture
    def svc(self, redis_store) -> SessionManager:
        return SessionManager(redis_store)

    # -----------------------------------------------------------------------
    # get_history()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_list_when_no_session(
        self, svc, redis_store
    ):
        redis_store.get = AsyncMock(return_value=None)
        result = await svc.get_history("user-123")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_returns_stored_messages(self, svc, redis_store):
        history = make_history(turns=2)
        redis_store.get = AsyncMock(return_value=json.dumps(history))

        result = await svc.get_history("user-123")

        assert len(result) == 4  # noqa: PLR2004
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "user message 0"

    @pytest.mark.asyncio
    async def test_get_history_uses_correct_key(self, svc, redis_store):
        redis_store.get = AsyncMock(return_value=None)
        await svc.get_history("user-abc")
        redis_store.get.assert_called_once_with("session:user-abc")

    @pytest.mark.asyncio
    async def test_get_history_raises_on_redis_failure(self, svc, redis_store):
        redis_store.get = AsyncMock(side_effect=Exception("connection refused"))

        with pytest.raises(SessionStoreUnavailableError):
            await svc.get_history("user-123")

    @pytest.mark.asyncio
    async def test_get_history_wraps_original_exception(self, svc, redis_store):
        original = Exception("timeout")
        redis_store.get = AsyncMock(side_effect=original)

        with pytest.raises(SessionStoreUnavailableError) as exc_info:
            await svc.get_history("user-123")

        assert exc_info.value.__cause__ is original

    # -----------------------------------------------------------------------
    # append_turn()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_append_turn_saves_user_and_assistant_messages(
        self, svc, redis_store
    ):
        redis_store.get = AsyncMock(return_value=None)

        await svc.append_turn("user-123", "How much vacation?", "You get 20 days.")

        saved = json.loads(redis_store.set.call_args[0][1])
        assert len(saved) == 2  # noqa: PLR2004
        assert saved[0] == {"role": "user", "content": "How much vacation?"}
        assert saved[1] == {"role": "assistant", "content": "You get 20 days."}

    @pytest.mark.asyncio
    async def test_append_turn_preserves_existing_history(self, svc, redis_store):
        existing = make_history(turns=1)
        redis_store.get = AsyncMock(return_value=json.dumps(existing))

        await svc.append_turn("user-123", "follow up?", "follow up answer.")

        saved = json.loads(redis_store.set.call_args[0][1])
        assert len(saved) == 4  # 2 existing + 2 new # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_append_turn_sets_ttl(self, svc, redis_store):
        redis_store.get = AsyncMock(return_value=None)

        await svc.append_turn("user-123", "question", "answer")

        call_kwargs = redis_store.set.call_args[1]
        assert call_kwargs["ttl"] == 3600  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_append_turn_trims_history_when_over_max_turns(
        self, svc, redis_store
    ):
        # max_conversation_turns=3, so max 6 messages (3 turns × 2 messages) # noqa: RUF003
        # seed with 3 existing turns (6 messages) then add 1 more
        existing = make_history(turns=3)
        redis_store.get = AsyncMock(return_value=json.dumps(existing))

        await svc.append_turn("user-123", "new question", "new answer")

        saved = json.loads(redis_store.set.call_args[0][1])
        assert (
            len(saved) == 6  # noqa: PLR2004
        )  # trimmed back to max (3 turns x 2 messages)

    @pytest.mark.asyncio
    async def test_append_turn_keeps_most_recent_messages_after_trim(
        self, svc, redis_store
    ):
        existing = make_history(turns=3)
        redis_store.get = AsyncMock(return_value=json.dumps(existing))

        await svc.append_turn("user-123", "newest question", "newest answer")

        saved = json.loads(redis_store.set.call_args[0][1])
        assert saved[-2]["content"] == "newest question"
        assert saved[-1]["content"] == "newest answer"

    @pytest.mark.asyncio
    async def test_append_turn_raises_on_save_failure(self, svc, redis_store):
        redis_store.get = AsyncMock(return_value=None)
        redis_store.set = AsyncMock(side_effect=Exception("write failed"))

        with pytest.raises(SessionStoreUnavailableError):
            await svc.append_turn("user-123", "question", "answer")

    # -----------------------------------------------------------------------
    # clear_session()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_clear_session_deletes_correct_key(self, svc, redis_store):
        await svc.clear_session("user-123")
        redis_store.delete.assert_called_once_with("session:user-123")

    @pytest.mark.asyncio
    async def test_clear_session_raises_on_delete_failure(self, svc, redis_store):
        redis_store.delete = AsyncMock(side_effect=Exception("delete failed"))

        with pytest.raises(SessionError):
            await svc.clear_session("user-123")

    # -----------------------------------------------------------------------
    # _key()
    # -----------------------------------------------------------------------

    def test_key_format(self, svc):
        assert svc._key("user-abc") == "session:user-abc"

    def test_key_is_unique_per_user(self, svc):
        assert svc._key("user-1") != svc._key("user-2")
