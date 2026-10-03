"""The minimal LLM client interface the pipeline depends on (injectable for tests)."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        """Send chat messages with `schema` as the structured-output format; return the raw
        assistant content. Raises ai.errors.AIUnavailable / AITimeout."""
        ...


def make_client(config=None) -> LLMClient:
    """The client for the configured LLM_PROVIDER (ollama by default)."""
    from ai.llm import groq_client, ollama_client
    from ai.llm.model_config import load_config

    config = config or load_config()
    if config.provider == "groq":
        return groq_client.GroqClient(config)
    return ollama_client.OllamaClient(config)


def check_available() -> tuple[bool, bool]:
    """(reachable, model_available) for the configured provider. Never raises."""
    from ai.llm import groq_client, ollama_client
    from ai.llm.model_config import load_config

    if load_config().provider == "groq":
        return groq_client.check_available()
    return ollama_client.check_available()
