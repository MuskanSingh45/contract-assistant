"""Model/runtime configuration for the LLM clients, read from the environment.

`LLM_PROVIDER` selects the runtime: `ollama` (local, default) or `groq` (hosted, OpenAI-compatible
API, used by the online deployment). Settings: docs/ai/model-config.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

PROVIDERS = ("ollama", "groq")
GROQ_DEFAULT_MODEL = "qwen/qwen3.8-27b"
# Groq's free tier allows about 8,000 tokens per minute, so its windows are smaller.
DEFAULT_WINDOW_TOKENS = {"ollama": 6000, "groq": 2500}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    model: str
    num_ctx: int
    timeout_seconds: float
    window_tokens: int
    api_key: str = ""


def fallback_provider() -> str | None:
    """`LLM_FALLBACK_PROVIDER`: used only when the primary provider is unavailable (empty = none)."""
    name = os.environ.get("LLM_FALLBACK_PROVIDER", "").strip().lower()
    if not name:
        return None
    if name not in PROVIDERS:
        raise ValueError(f"LLM_FALLBACK_PROVIDER must be one of {PROVIDERS}, got {name!r}")
    return name


def load_config(provider: str | None = None) -> ModelConfig:
    """Read the AI settings documented in docs/ai/model-config.md (defaults match .env.example).

    `provider` overrides LLM_PROVIDER (used to build the fallback's config)."""
    provider = provider or os.environ.get("LLM_PROVIDER", "ollama").strip().lower() or "ollama"
    if provider not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
    if provider == "groq":
        base_url = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.environ.get("GROQ_MODEL", GROQ_DEFAULT_MODEL)
        api_key = os.environ.get("GROQ_API_KEY", "")
    else:
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        api_key = ""
    return ModelConfig(
        provider=provider,
        base_url=base_url.rstrip("/"),
        model=model,
        num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
        timeout_seconds=float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "300")),
        window_tokens=int(os.environ.get("EXTRACTION_WINDOW_TOKENS") or DEFAULT_WINDOW_TOKENS[provider]),
        api_key=api_key,
    )


def estimate_tokens(text: str) -> int:
    """Rough token estimate used for windowing and the context guard (characters / 4)."""
    return (len(text) + 3) // 4
