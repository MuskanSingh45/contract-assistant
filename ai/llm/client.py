"""The minimal LLM client interface the pipeline depends on (injectable for tests)."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        """Send chat messages with `schema` as the structured-output format; return the raw
        assistant content. Raises ai.errors.AIUnavailable / AITimeout."""
        ...
