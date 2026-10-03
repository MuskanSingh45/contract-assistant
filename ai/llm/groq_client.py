"""Groq client (OpenAI-compatible chat completions), used by the online deployment.

Same contract as OllamaClient: `chat()` returns the raw assistant content and raises
AIUnavailable / AITimeout. The JSON Schema is sent as a non-strict `json_schema` response
format (strict mode fails on Groq for our schemas); the pipeline validates and retries anyway.
Free-tier rate limits (429) are handled by waiting for `retry-after` and trying again.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ai.errors import AITimeout, AIUnavailable
from ai.llm.model_config import ModelConfig, load_config

logger = logging.getLogger(__name__)

MAX_RATE_LIMIT_WAITS = 6
MAX_WAIT_SECONDS = 60.0


class GroqClient:
    def __init__(self, config: ModelConfig | None = None, sleep=time.sleep) -> None:
        self.config = config or load_config()
        self.model = self.config.model
        self._sleep = sleep

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        if not self.config.api_key:
            raise AIUnavailable("GROQ_API_KEY is not set")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0,
            "seed": 42,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": schema, "strict": False},
            },
        }
        started = time.monotonic()
        for attempt in range(MAX_RATE_LIMIT_WAITS + 1):
            response = self._post(payload)
            if response.status_code != 429:
                break
            if attempt == MAX_RATE_LIMIT_WAITS:
                raise AIUnavailable("Groq rate limit: still limited after waiting; try again in a minute")
            wait = _retry_after(response)
            logger.info(
                "Groq rate limit reached; waiting %.0fs",
                wait,
                extra={"event": "llm.rate_limited", "wait_s": wait, "attempt": attempt + 1},
            )
            self._sleep(wait)

        if response.status_code in (401, 403):
            raise AIUnavailable(f"Groq rejected the API key (HTTP {response.status_code})")
        if response.status_code == 404:
            raise AIUnavailable(f"Model {self.config.model!r} is not available on Groq")
        if response.status_code >= 400:
            raise AIUnavailable(f"Groq returned HTTP {response.status_code}: {_error_text(response)}")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIUnavailable("Unexpected response shape from Groq") from exc
        usage = body.get("usage") or {}
        seconds = time.monotonic() - started
        logger.info(
            "Groq call: prompt_tokens=%s output_tokens=%s seconds=%.1f",
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            seconds,
            extra={
                "event": "llm.call",
                "model": self.config.model,
                "prompt_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "duration_s": round(seconds, 2),
            },
        )
        return content

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        url = f"{self.config.base_url}/chat/completions"
        timeout = httpx.Timeout(self.config.timeout_seconds, connect=10.0)
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            return httpx.post(url, json=payload, headers=headers, timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise AIUnavailable(f"Cannot reach Groq at {self.config.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise AITimeout(f"Groq did not respond within {self.config.timeout_seconds:.0f}s") from exc
        except httpx.HTTPError as exc:
            raise AIUnavailable(f"Groq request failed: {exc}") from exc


def _retry_after(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("retry-after", "10"))
    except ValueError:
        seconds = 10.0
    return min(max(seconds, 1.0), MAX_WAIT_SECONDS)


def _error_text(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return response.text[:300]


def check_available() -> tuple[bool, bool]:
    """(reachable, model_available) via GET /models with a 5s timeout. Never raises."""
    config = load_config()
    if not config.api_key:
        return False, False
    try:
        response = httpx.get(
            f"{config.base_url}/models", headers={"Authorization": f"Bearer {config.api_key}"}, timeout=5.0
        )
        response.raise_for_status()
        ids = {m.get("id") for m in response.json().get("data", [])}
    except Exception:  # noqa: BLE001 - health check must never raise
        return False, False
    return True, config.model in ids
