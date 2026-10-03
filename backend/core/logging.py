"""Logging setup and per-request context.

Every log line carries the request ID of the HTTP request that caused it (``-`` outside a request),
including the background analysis started by ``POST /analyze``. The same ID is returned to the
client in the ``X-Request-ID`` header and in error bodies, so a message shown in the UI can be
matched to the server log. With ``LOG_FORMAT=json`` each line is a JSON object carrying the same
fields plus the call site's ``extra=`` fields (``event``, ``version_id``, ...).
Docs: docs/architecture/backend-architecture.md (Logging).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.core.config import settings

REQUEST_ID_HEADER = "X-Request-ID"
FORMAT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_CLIENT_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

access_log = logging.getLogger("backend.access")


# Attributes every LogRecord has; anything else on a record came from ``extra=``.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "request_id"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, request_id, message, [exc], plus ``extra=`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC)
        entry = {
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            entry["exc"] = record.exc_text
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


def make_formatter(fmt: str) -> logging.Formatter:
    """``json`` -> JsonFormatter; anything else -> the text FORMAT."""
    return JsonFormatter() if fmt.lower() == "json" else logging.Formatter(FORMAT)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging(level: str | None = None, log_file: str | None = None, fmt: str | None = None) -> None:
    """Console + optional rotating file handler, text or JSON. Safe to call more than once (reload, tests)."""
    level = (level or settings.log_level).upper()
    log_file = settings.log_file if log_file is None else log_file
    formatter = make_formatter(fmt or settings.log_format)

    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_contract_assistant", False)]:
        root.removeHandler(handler)
        handler.close()

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
    for handler in handlers:
        handler._contract_assistant = True  # type: ignore[attr-defined]
        handler.setFormatter(formatter)
        handler.addFilter(_RequestIdFilter())
        root.addHandler(handler)
    root.setLevel(level)

    # Our access log replaces uvicorn's (it adds the request ID and duration).
    logging.getLogger("uvicorn.access").disabled = True
    # Third-party chatter (one line per Ollama call) is not useful at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


class RequestContextMiddleware:
    """Pure ASGI middleware: assigns the request ID, echoes it back, and writes one access line.

    A client-supplied ``X-Request-ID`` is reused when it looks safe, so a caller can correlate.
    Successful polling of the analysis status is logged at DEBUG to keep the log readable.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers") or []).get(REQUEST_ID_HEADER.lower().encode(), b"").decode()
        request_id = incoming if _CLIENT_ID.match(incoming) else new_request_id()
        request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            ms = (time.perf_counter() - started) * 1000
            path = scope["path"] + (f"?{scope['query_string'].decode()}" if scope.get("query_string") else "")
            level = logging.INFO
            if status >= 500:
                level = logging.ERROR
            elif status >= 400:
                level = logging.WARNING
            elif scope["method"] in ("GET", "OPTIONS") and (
                scope["path"].endswith("/analysis") or scope["path"] == "/api/health"
            ):
                level = logging.DEBUG
            access_log.log(
                level,
                "%s %s -> %d (%.0f ms)",
                scope["method"],
                path,
                status,
                ms,
                extra={
                    "event": "http.request",
                    "method": scope["method"],
                    "path": path,
                    "status": status,
                    "duration_ms": round(ms, 1),
                },
            )
