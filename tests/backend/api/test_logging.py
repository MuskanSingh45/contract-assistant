"""Request IDs, error bodies and logs: docs/api/errors.md, docs/architecture/backend-architecture.md."""

import io
import json
import logging
import re

from backend.core.logging import FORMAT, JsonFormatter, RequestContextMiddleware, _RequestIdFilter, setup_logging


def test_every_response_carries_a_request_id(client):
    resp = client.get("/api/contracts")
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"].startswith("req_")


def test_client_request_id_is_reused_when_safe(client):
    assert client.get("/api/contracts", headers={"X-Request-ID": "demo-123"}).headers["X-Request-ID"] == "demo-123"
    unsafe = client.get("/api/contracts", headers={"X-Request-ID": "bad id\nwith newline"}).headers["X-Request-ID"]
    assert unsafe.startswith("req_")


def test_error_body_has_request_id_matching_header(client):
    resp = client.get("/api/contracts/nope")
    body = resp.json()["error"]
    assert body["code"] == "CONTRACT_NOT_FOUND"
    assert body["request_id"] == resp.headers["X-Request-ID"]


def test_unknown_route_and_wrong_method(client):
    assert client.get("/api/does-not-exist").json()["error"]["code"] == "NOT_FOUND"
    assert client.delete("/api/contracts").json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_errors_and_access_lines_are_logged_with_request_id(client, caplog):
    caplog.set_level(logging.INFO)
    resp = client.get("/api/contracts/nope")
    rid = resp.headers["X-Request-ID"]
    error = next(r for r in caplog.records if "CONTRACT_NOT_FOUND (404)" in r.getMessage())
    access = next(r for r in caplog.records if r.name == "backend.access")
    assert access.getMessage().startswith("GET /api/contracts/nope -> 404")
    assert access.levelno == logging.WARNING
    assert error.request_id == access.request_id == rid


def test_unexpected_error_is_generic_logged_and_traceable(client, caplog, monkeypatch):
    from backend.services import contract_service

    def boom(*_a, **_k):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(contract_service, "list_contracts", boom)
    caplog.set_level(logging.INFO)
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/contracts")
    assert resp.status_code == 500
    err = resp.json()["error"]
    assert err["code"] == "INTERNAL_ERROR"
    assert "secret" not in err["message"]
    assert err["request_id"] == resp.headers["X-Request-ID"]
    tb = next(r for r in caplog.records if r.getMessage().startswith("Unhandled error"))
    assert tb.exc_info is not None
    assert tb.request_id == err["request_id"]


def test_background_analysis_logs_carry_the_analyze_request_id(client, caplog, monkeypatch):
    from pathlib import Path

    from ai.errors import InvalidAIOutput
    from backend.services import analysis_service

    def boom(segs, on_progress=None):
        raise InvalidAIOutput("bad output")

    monkeypatch.setattr(analysis_service, "analyze", boom)
    pdf = Path(__file__).resolve().parents[3] / "contracts/samples/simple/acme-services-agreement.pdf"
    with pdf.open("rb") as f:
        cid = client.post("/api/contracts", files={"file": ("acme.pdf", f)}).json()["contract"]["id"]
    caplog.set_level(logging.INFO)
    client.post(f"/api/contracts/{cid}/analyze", headers={"X-Request-ID": "analyze-1"})
    analysis = [r for r in caplog.records if r.name == "backend.services.analysis_service"]
    messages = [r.getMessage() for r in analysis]
    assert any("started" in m for m in messages)
    assert any("failed: INVALID_AI_OUTPUT" in m for m in messages)
    assert {r.request_id for r in analysis} == {"analyze-1"}


def test_setup_logging_is_idempotent_and_writes_file(tmp_path):
    log_file = tmp_path / "logs" / "app.log"
    setup_logging("INFO", str(log_file))
    setup_logging("INFO", str(log_file))
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_contract_assistant", False)]
    assert len(ours) == 2  # console + file, not duplicated
    logging.getLogger("test").info("hello file")
    for h in ours:
        h.flush()
    assert "hello file" in log_file.read_text()
    setup_logging("INFO", "")


def test_middleware_ignores_non_http_scopes():
    called = []

    async def app(scope, receive, send):
        called.append(scope["type"])

    import asyncio

    asyncio.run(RequestContextMiddleware(app)({"type": "lifespan"}, None, None))
    assert called == ["lifespan"]


def _record(msg="hello %s", args=("world",), exc_info=None, **extra) -> logging.LogRecord:
    record = logging.LogRecord("ai.test", logging.INFO, __file__, 1, msg, args, exc_info)
    record.request_id = "req_abc"
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_one_object_with_core_and_extra_fields():
    line = JsonFormatter().format(_record(event="llm.call", prompt_tokens=12, stats={"retries": 1}))
    assert "\n" not in line
    entry = json.loads(line)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", entry["ts"])
    assert entry["level"] == "INFO"
    assert entry["logger"] == "ai.test"
    assert entry["request_id"] == "req_abc"
    assert entry["message"] == "hello world"
    assert entry["event"] == "llm.call" and entry["prompt_tokens"] == 12 and entry["stats"] == {"retries": 1}
    assert "exc" not in entry and "args" not in entry and "msg" not in entry


def test_json_formatter_includes_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        entry = json.loads(JsonFormatter().format(_record(exc_info=sys.exc_info())))
    assert "ValueError: boom" in entry["exc"]


def test_text_format_is_unchanged():
    line = logging.Formatter(FORMAT).format(_record(event="llm.call"))
    assert re.search(r" INFO    \[req_abc\] ai\.test: hello world$", line)
    assert "llm.call" not in line


def test_setup_logging_json_writes_json_lines(tmp_path):
    log_file = tmp_path / "app.log"
    setup_logging("INFO", str(log_file), fmt="json")
    try:
        logging.getLogger("test").info("hello %s", "json", extra={"event": "test.event", "version_id": "v1"})
        for h in logging.getLogger().handlers:
            h.flush()
        entry = json.loads(log_file.read_text().strip().splitlines()[-1])
    finally:
        setup_logging("INFO", "", fmt="text")
    assert entry["message"] == "hello json"
    assert entry["event"] == "test.event" and entry["version_id"] == "v1"
    assert entry["request_id"] == "-"


def test_http_request_in_json_mode_has_structured_access_and_error_fields(client):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_RequestIdFilter())
    root = logging.getLogger()
    root.addHandler(handler)
    old_level = root.level
    root.setLevel(logging.INFO)
    try:
        resp = client.get("/api/contracts/nope")
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
    entries = [json.loads(line) for line in stream.getvalue().splitlines()]
    access = next(e for e in entries if e["logger"] == "backend.access")
    assert access["event"] == "http.request"
    assert access["method"] == "GET" and access["path"] == "/api/contracts/nope"
    assert access["status"] == 404 and isinstance(access["duration_ms"], float)
    assert access["request_id"] == resp.headers["X-Request-ID"]
    error = next(e for e in entries if e.get("event") == "http.error")
    assert error["error_code"] == "CONTRACT_NOT_FOUND" and error["status"] == 404


def test_root_points_to_api_and_docs(client):
    body = client.get("/").json()
    assert body["docs"] == "/docs" and body["health"] == "/api/health"
