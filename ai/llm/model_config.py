"""Model/runtime configuration for the Ollama client, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str
    num_ctx: int
    timeout_seconds: float
    window_tokens: int


def load_config() -> ModelConfig:
    """Read the AI settings documented in docs/ai/model-config.md (defaults match .env.example)."""
    return ModelConfig(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        model=os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
        num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
        timeout_seconds=float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "300")),
        window_tokens=int(os.environ.get("EXTRACTION_WINDOW_TOKENS", "6000")),
    )


def estimate_tokens(text: str) -> int:
    """Rough token estimate used for windowing and the context guard (characters / 4)."""
    return (len(text) + 3) // 4
