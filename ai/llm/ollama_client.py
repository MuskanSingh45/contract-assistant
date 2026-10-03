"""Ollama /api/chat client. Settings per docs/ai/model-config.md."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ai.errors import AITimeout, AIUnavailable
from ai.llm.model_config import ModelConfig, estimate_tokens, load_config

logger = logging.getLogger(__name__)

NO_THINK = "/no_think"
CONTEXT_GUARD_RATIO = 0.75


class OllamaClient:
    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or load_config()
        self.model = self.config.model

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        messages = [_with_no_think(m) for m in messages]
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in messages)
        if prompt_tokens > CONTEXT_GUARD_RATIO * self.config.num_ctx:
            # Windowing keeps prompts far below this; reaching it is a programming error.
            raise ValueError(f"Prompt (~{prompt_tokens} tokens) exceeds 75% of num_ctx={self.config.num_ctx}")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "format": schema,
            "think": False,
            "stream": False,
            "options": {"num_ctx": self.config.num_ctx, "temperature": 0, "seed": 42},
        }
        url = f"{self.config.base_url}/api/chat"
        timeout = httpx.Timeout(self.config.timeout_seconds, connect=5.0)
        try:
            response = httpx.post(url, json=payload, timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise AIUnavailable(f"Cannot reach Ollama at {self.config.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise AITimeout(f"Ollama did not respond within {self.config.timeout_seconds:.0f}s") from exc
        except httpx.HTTPError as exc:
            raise AIUnavailable(f"Ollama request failed: {exc}") from exc

        if response.status_code == 404:
            raise AIUnavailable(f"Model {self.config.model!r} is not available in Ollama")
        if response.status_code >= 400:
            raise AIUnavailable(f"Ollama returned HTTP {response.status_code}: {response.text[:300]}")
        try:
            body = response.json()
            content = body["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AIUnavailable("Unexpected response shape from Ollama") from exc
        prompt_tokens, output_tokens = body.get("prompt_eval_count"), body.get("eval_count")
        seconds = (body.get("total_duration") or 0) / 1e9
        logger.info(
            "Ollama call: prompt_tokens=%s output_tokens=%s seconds=%.1f",
            prompt_tokens,
            output_tokens,
            seconds,
            extra={
                "event": "llm.call",
                "model": self.config.model,
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "duration_s": round(seconds, 2),
            },
        )
        return content


def _with_no_think(message: dict[str, str]) -> dict[str, str]:
    if message["role"] != "user" or message["content"].rstrip().endswith(NO_THINK):
        return message
    return {**message, "content": f"{message['content']}\n{NO_THINK}"}


def check_available() -> tuple[bool, bool]:
    """(reachable, model_available) via GET /api/tags with a 3s timeout. Never raises."""
    config = load_config()
    try:
        response = httpx.get(f"{config.base_url}/api/tags", timeout=3.0)
        response.raise_for_status()
        models = response.json().get("models", [])
    except Exception:  # noqa: BLE001 - health check must never raise
        return False, False
    wanted = {config.model, f"{config.model}:latest"}
    names = {m.get("name") for m in models} | {m.get("model") for m in models}
    return True, bool(wanted & names)
