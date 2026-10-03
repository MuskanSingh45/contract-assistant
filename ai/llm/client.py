"""The minimal LLM client interface the pipeline depends on (injectable for tests)."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        """Send chat messages with `schema` as the structured-output format; return the raw
        assistant content. Raises ai.errors.AIUnavailable / AITimeout."""
        ...


def available_for(config) -> tuple[bool, bool]:
    """(reachable, model_available) for one provider's config. Never raises."""
    from ai.llm import groq_client, ollama_client

    if config.provider == "groq":
        return groq_client.check_available(config)
    return ollama_client.check_available(config)


def active_config():
    """The provider to use now: the primary (LLM_PROVIDER), or LLM_FALLBACK_PROVIDER when the
    primary is unreachable or lacks the model and the fallback is available. Never raises on
    availability; returns the primary if neither is available (the caller reports AI_UNAVAILABLE)."""
    import logging

    from ai.llm.model_config import fallback_provider, load_config

    primary = load_config()
    fallback = fallback_provider()
    if not fallback or fallback == primary.provider or all(available_for(primary)):
        return primary
    secondary = load_config(fallback)
    if all(available_for(secondary)):
        logging.getLogger(__name__).warning(
            "Primary model provider %s unavailable; using fallback %s",
            primary.provider,
            fallback,
            extra={"event": "llm.fallback", "primary": primary.provider, "fallback": fallback},
        )
        return secondary
    return primary


def make_client(config=None) -> LLMClient:
    """The client for `config`, or for the active provider (primary, else fallback)."""
    from ai.llm import groq_client, ollama_client

    config = config or active_config()
    if config.provider == "groq":
        return groq_client.GroqClient(config)
    return ollama_client.OllamaClient(config)


def check_available() -> tuple[bool, bool]:
    """(reachable, model_available) for the active provider. Never raises."""
    return available_for(active_config())
