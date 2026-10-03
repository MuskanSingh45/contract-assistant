"""Groq (OpenAI-compatible) client: request shape, rate-limit waits, errors, health check."""

import httpx
import pytest

from ai.errors import AITimeout, AIUnavailable
from ai.llm import client as llm_client
from ai.llm import groq_client
from ai.llm.groq_client import GroqClient
from ai.llm.model_config import load_config
from ai.llm.ollama_client import OllamaClient

SCHEMA = {"type": "object"}
MESSAGES = [{"role": "user", "content": "hello"}]
OK = {"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}


@pytest.fixture
def groq_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("EXTRACTION_WINDOW_TOKENS", raising=False)


def _responses(*responses, captured=None):
    queue = list(responses)

    def fake_post(url, json, headers, timeout):
        if captured is not None:
            captured.append({"url": url, "json": json, "headers": headers})
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return fake_post


def test_config_selects_groq_with_smaller_windows(groq_env):
    config = load_config()
    assert config.provider == "groq"
    assert config.model == "qwen/qwen3.8-27b"
    assert config.window_tokens == 2500
    assert isinstance(llm_client.make_client(config), GroqClient)


def test_default_provider_is_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(llm_client.make_client(), OllamaClient)


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        load_config()


def test_request_shape(groq_env, monkeypatch):
    captured = []
    monkeypatch.setattr(httpx, "post", _responses(httpx.Response(200, json=OK), captured=captured))
    assert GroqClient().chat(MESSAGES, SCHEMA) == "{}"
    call = captured[0]
    assert call["url"].endswith("/chat/completions")
    assert call["headers"]["Authorization"] == "Bearer test-key"
    body = call["json"]
    assert body["temperature"] == 0 and body["model"] == "qwen/qwen3.8-27b"
    assert body["response_format"]["json_schema"] == {"name": "extraction", "schema": SCHEMA, "strict": False}


def test_rate_limit_waits_for_retry_after_then_succeeds(groq_env, monkeypatch):
    waits = []
    limited = httpx.Response(429, headers={"retry-after": "7"}, json={"error": {"message": "rate limit"}})
    monkeypatch.setattr(httpx, "post", _responses(limited, httpx.Response(200, json=OK)))
    assert GroqClient(sleep=waits.append).chat(MESSAGES, SCHEMA) == "{}"
    assert waits == [7.0]


def test_rate_limit_gives_up_after_max_waits(groq_env, monkeypatch):
    limited = httpx.Response(429, headers={"retry-after": "999"})
    monkeypatch.setattr(httpx, "post", _responses(*[limited] * (groq_client.MAX_RATE_LIMIT_WAITS + 1)))
    waits = []
    with pytest.raises(AIUnavailable, match="rate limit"):
        GroqClient(sleep=waits.append).chat(MESSAGES, SCHEMA)
    assert waits and max(waits) == groq_client.MAX_WAIT_SECONDS  # capped


@pytest.mark.parametrize(
    "response, match",
    [
        (httpx.Response(401, json={}), "API key"),
        (httpx.Response(404, json={}), "not available"),
        (httpx.Response(500, json={"error": {"message": "boom"}}), "HTTP 500: boom"),
        (httpx.Response(200, json={"choices": []}), "Unexpected response"),
    ],
)
def test_http_errors_become_ai_unavailable(groq_env, monkeypatch, response, match):
    monkeypatch.setattr(httpx, "post", _responses(response))
    with pytest.raises(AIUnavailable, match=match):
        GroqClient().chat(MESSAGES, SCHEMA)


def test_network_errors(groq_env, monkeypatch):
    monkeypatch.setattr(httpx, "post", _responses(httpx.ConnectError("down")))
    with pytest.raises(AIUnavailable):
        GroqClient().chat(MESSAGES, SCHEMA)
    monkeypatch.setattr(httpx, "post", _responses(httpx.ReadTimeout("slow")))
    with pytest.raises(AITimeout):
        GroqClient().chat(MESSAGES, SCHEMA)


def test_missing_key_is_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(AIUnavailable, match="GROQ_API_KEY"):
        GroqClient().chat(MESSAGES, SCHEMA)
    assert groq_client.check_available() == (False, False)


def test_check_available(groq_env, monkeypatch):
    models = httpx.Response(200, json={"data": [{"id": "qwen/qwen3.8-27b"}]}, request=httpx.Request("GET", "x"))
    monkeypatch.setattr(httpx, "get", lambda url, headers, timeout: models)
    assert llm_client.check_available() == (True, True)
    other = httpx.Response(200, json={"data": [{"id": "other"}]}, request=httpx.Request("GET", "x"))
    monkeypatch.setattr(httpx, "get", lambda url, headers, timeout: other)
    assert groq_client.check_available() == (True, False)

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    assert groq_client.check_available() == (False, False)


def test_fallback_used_only_when_primary_is_down(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from ai.llm import ollama_client

    monkeypatch.setattr(groq_client, "check_available", lambda config=None: (True, True))
    monkeypatch.setattr(ollama_client, "check_available", lambda config=None: (True, True))
    assert llm_client.active_config().provider == "ollama"
    assert isinstance(llm_client.make_client(), OllamaClient)

    monkeypatch.setattr(ollama_client, "check_available", lambda config=None: (False, False))
    assert llm_client.active_config().provider == "groq"
    assert isinstance(llm_client.make_client(), GroqClient)
    assert llm_client.check_available() == (True, True)

    monkeypatch.setattr(groq_client, "check_available", lambda config=None: (False, False))
    assert llm_client.active_config().provider == "ollama"  # neither up: report the primary
    assert llm_client.check_available() == (False, False)


def test_no_fallback_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("LLM_FALLBACK_PROVIDER", raising=False)
    from ai.llm import ollama_client

    monkeypatch.setattr(ollama_client, "check_available", lambda config=None: (False, False))
    assert llm_client.active_config().provider == "ollama"


def test_invalid_fallback_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "nope")
    from ai.llm.model_config import fallback_provider

    with pytest.raises(ValueError):
        fallback_provider()
