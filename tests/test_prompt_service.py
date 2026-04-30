from pathlib import Path

import pytest

from app.services.prompt_service import PromptService
from app.services.retrieval_service import DocumentChunk

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def make_chunk(
    content="You get 20 vacation days per year.",
    source="hr-policy.pdf",
    score=0.92,
    id=1,
    metadata=None,
) -> DocumentChunk:
    return DocumentChunk(
        id=id,
        content=content,
        source=source,
        score=score,
        metadata=metadata or {},
    )


def make_history():
    return [
        {"role": "user", "content": "What is the sick leave policy?"},
        {"role": "assistant", "content": "You get 10 sick days per year."},
    ]


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------


class TestPromptService:
    @pytest.fixture
    def svc(self, tmp_path: Path) -> PromptService:
        """Create a PromptService pointed at a temporary prompts directory
        with a minimal system prompt template."""
        template = tmp_path / "hr_system_prompt.j2"
        template.write_text(
            "You are an HR assistant.\n"
            "Today: {{ today }}\n"
            "{% if employee_name %}Employee: {{ employee_name }}{% endif %}\n"
            "{% if company_name %}Company: {{ company_name }}{% endif %}\n"
            "{% for chunk in context_chunks %}"
            "Source: {{ chunk.source }}\n{{ chunk.content }}\n"
            "{% endfor %}"
        )
        return PromptService(prompts_dir=tmp_path)

    # -----------------------------------------------------------------------
    # build_messages() — structure
    # -----------------------------------------------------------------------

    def test_returns_list_of_messages(self, svc):
        messages = svc.build_messages(query="How much vacation do I get?", chunks=[])
        assert isinstance(messages, list)
        assert len(messages) >= 1

    def test_first_message_is_system(self, svc):
        messages = svc.build_messages(query="How much vacation do I get?", chunks=[])
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    def test_last_message_is_user_query(self, svc):
        messages = svc.build_messages(query="How much vacation do I get?", chunks=[])
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "How much vacation do I get?"

    def test_message_count_without_history(self, svc):
        # system + user = 2 messages
        expected_count = 2
        messages = svc.build_messages(query="test", chunks=[])
        assert len(messages) == expected_count

    def test_message_count_with_history(self, svc):
        # system + 2 history turns + user = 4 messages
        expected_count = 4
        messages = svc.build_messages(
            query="test",
            chunks=[],
            history=make_history(),
        )
        assert len(messages) == expected_count

    def test_history_inserted_between_system_and_user(self, svc):
        history = make_history()
        messages = svc.build_messages(query="follow up", chunks=[], history=history)

        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is the sick leave policy?"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "follow up"

    def test_none_history_is_ignored(self, svc):
        expected_count = 2  # system + user
        messages = svc.build_messages(query="test", chunks=[], history=None)
        assert len(messages) == expected_count

    # -----------------------------------------------------------------------
    # build_messages() — system prompt content
    # -----------------------------------------------------------------------

    def test_system_prompt_contains_chunk_content(self, svc):
        chunk = make_chunk(content="Employees receive 20 vacation days.")
        messages = svc.build_messages(query="test", chunks=[chunk])
        assert "Employees receive 20 vacation days." in messages[0]["content"]

    def test_system_prompt_contains_chunk_source(self, svc):
        chunk = make_chunk(source="benefits-guide.pdf")
        messages = svc.build_messages(query="test", chunks=[chunk])
        assert "benefits-guide.pdf" in messages[0]["content"]

    def test_system_prompt_contains_multiple_chunks(self, svc):
        chunks = [
            make_chunk(content="Vacation policy content.", source="vacation.pdf", id=1),
            make_chunk(
                content="Sick leave policy content.", source="sick-leave.pdf", id=2
            ),
        ]
        messages = svc.build_messages(query="test", chunks=chunks)
        system = messages[0]["content"]

        assert "Vacation policy content." in system
        assert "Sick leave policy content." in system

    def test_system_prompt_contains_today_date(self, svc):
        messages = svc.build_messages(query="test", chunks=[])
        # date is rendered as "Month DD, YYYY" e.g. "April 12, 2026"
        assert "2026" in messages[0]["content"]

    def test_system_prompt_contains_employee_name(self, svc):
        messages = svc.build_messages(
            query="test", chunks=[], employee_name="Jane Smith"
        )
        assert "Jane Smith" in messages[0]["content"]

    def test_system_prompt_contains_company_name(self, svc):
        messages = svc.build_messages(query="test", chunks=[], company_name="Acme Corp")
        assert "Acme Corp" in messages[0]["content"]

    def test_system_prompt_omits_employee_name_when_not_provided(self, svc):
        messages = svc.build_messages(query="test", chunks=[])
        assert "Employee:" not in messages[0]["content"]

    def test_empty_chunks_renders_without_error(self, svc):
        messages = svc.build_messages(query="test", chunks=[])
        assert messages[0]["role"] == "system"

    # -----------------------------------------------------------------------
    # Template loading
    # -----------------------------------------------------------------------

    def test_raises_if_template_missing(self, tmp_path):
        """PromptService pointed at an empty directory should raise on render."""
        svc = PromptService(prompts_dir=tmp_path)
        with pytest.raises(SyntaxError):
            svc.build_messages(query="test", chunks=[])
