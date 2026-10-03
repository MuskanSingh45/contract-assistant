"""Request limits: a sliding-window rate limiter and an early upload-size check."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque

from backend.core.config import settings
from backend.core.logging import request_id_var

# Multipart overhead allowed on top of MAX_UPLOAD_MB before the body is even read.
_MULTIPART_SLACK_BYTES = 1024 * 1024


class RateLimiter:
    """In-memory sliding-window limiter (single process, as on the free host)."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


class UploadSizeLimitMiddleware:
    """Rejects an oversized request from its Content-Length header, before the body is read.

    The service checks the exact file size too; this stops a huge upload from filling memory
    or disk on a small host first. Responds with the documented FILE_TOO_LARGE error.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH"):
            length = dict(scope.get("headers") or []).get(b"content-length", b"0")
            limit = settings.max_upload_mb * 1024 * 1024 + _MULTIPART_SLACK_BYTES
            if length.isdigit() and int(length) > limit:
                body = json.dumps(
                    {
                        "error": {
                            "code": "FILE_TOO_LARGE",
                            "message": f"File is larger than {settings.max_upload_mb} MB.",
                            "details": None,
                            "request_id": request_id_var.get(),
                        }
                    }
                ).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 413,
                        # X-Request-ID is added by the outer RequestContextMiddleware.
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
