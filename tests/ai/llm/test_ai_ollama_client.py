import httpx
import pytest

from ai.errors import AITimeout, AIUnavailable
from ai.llm import ollama_client
from ai.llm.model_config import load_config
from ai.llm.ollama_client import OllamaClient, check_available

SCHEMA = {"type": "object"}
MESSAGES = [{"role": "user", "content": "hello"}]


def _post_returning(response=None, exc=None, captured=None):
    def fake_post(url, json, timeout):
        if captured is not None:
            captured.update(url=url, json=json)
        if exc:
            raise exc
        return response

    return fake_post


def test_request_payload(monkeypatch):
    captured = {}
    resp = httpx.Response(200, json={"message": {"content": "{}"}})
    monkeypatch.setattr(httpx, "post", _post_returning(resp, captured=captured))
    assert OllamaClient().chat(MESSAGES, SCHEMA) == "{}"
    body = captured["json"]
    assert captured["url"].endswith("/api/chat")
    assert body["format"] == SCHEMA and body["think"] is False and body["stream"] is False
    assert body["options"] == {
        "num_ctx": load_config().num_ctx,
        "temperature": 0,
        "seed": 42,
    }
    assert body["messages"][0]["content"].endswith("/no_think")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ConnectError("refused"), AIUnavailable),
        (httpx.ReadTimeout("slow"), AITimeout),
    ],
)
def test_transport_errors_are_mapped(monkeypatch, exc, expected):
    monkeypatch.setattr(httpx, "post", _post_returning(exc=exc))
    with pytest.raises(expected):
        OllamaClient().chat(MESSAGES, SCHEMA)


def test_model_not_found_is_unavailable(monkeypatch):
    resp = httpx.Response(404, json={"error": "model 'x' not found"})
    monkeypatch.setattr(httpx, "post", _post_returning(resp))
    with pytest.raises(AIUnavailable):
        OllamaClient().chat(MESSAGES, SCHEMA)


def test_context_guard(monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "100")
    with pytest.raises(ValueError):
        OllamaClient().chat([{"role": "user", "content": "x" * 400}], SCHEMA)


def test_check_available(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    tags = httpx.Response(
        200,
        json={"models": [{"name": "qwen3:8b"}]},
        request=httpx.Request("GET", "http://x"),
    )
    monkeypatch.setattr(ollama_client.httpx, "get", lambda url, timeout: tags)
    assert check_available() == (True, True)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3:8b")
    assert check_available() == (True, False)

    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(ollama_client.httpx, "get", boom)
    assert check_available() == (False, False)
