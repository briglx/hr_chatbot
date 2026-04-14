"""Prompt service — renders Jinja2 templates into LLM message lists.

This service has no network calls. It takes retrieved document chunks
and conversation history, and assembles the final message list that
gets passed to LLMService.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.config.settings import get_settings
from app.memory.session_manager import Message
from app.services.retrieval_service import DocumentChunk

PROMPTS_DIR = Path(__file__).parents[2] / "prompts"


class PromptService:
    """Render Jinja2 prompt templates and assemble message lists for the LLM."""

    def __init__(
        self, prompts_dir: Path = PROMPTS_DIR, template: str | None = None
    ) -> None:
        self._settings = get_settings()
        self._template = template or self._settings.prompt_template
        self._env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_messages(
        self,
        query: str,
        chunks: list[DocumentChunk],
        history: list[Message] | None = None,
        *,
        employee_name: str | None = None,
        company_name: str | None = None,
    ) -> list[Message]:
        """Assemble the full message list to send to LLMService.

        Layout:
            [system prompt with retrieved HR context]
            [conversation history — alternating user/assistant turns]
            [current user query]

        Args:
            query: The current user question (already PII-filtered).
            chunks: Retrieved document chunks from RetrievalService.
            history: Previous turns from SessionManager.
            employee_name: Optional — personalises the system prompt.
            company_name: Optional — customises the company name in the prompt.

        Returns:
            List of Message dicts ready to pass to LLMService.complete().
        """
        system_content = self._render_system_prompt(
            chunks=chunks,
            employee_name=employee_name,
            company_name=company_name,
        )

        messages: list[Message] = [{"role": "system", "content": system_content}]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": query})
        return messages

    def _render_system_prompt(
        self,
        chunks: list[DocumentChunk],
        employee_name: str | None = None,
        company_name: str | None = None,
    ) -> str:
        template = self._env.get_template(self._template)
        return template.render(
            context_chunks=chunks,
            today=date.today().strftime("%B %d, %Y"),
            employee_name=employee_name,
            company_name=company_name,
        )
