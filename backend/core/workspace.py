"""Per-browser workspaces for the public deployment (WORKSPACES=true).

Each browser sends a random `X-Workspace-ID`. Every workspace has its **own SQLite file**
(`WORKSPACE_DIR/<id>.db`), created on first use with the migrations and the demo data, so one
visitor's uploads and review decisions can never be read or changed from another workspace:
there is no shared table to filter wrongly. Requests without the header (health checks, the
API docs page, local use) use the default database (`DATABASE_PATH`).

Locally WORKSPACES is off: the header is ignored and everything uses `data/app.db`.
Docs: docs/architecture/backend-architecture.md (Workspaces).
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

from fastapi import Request

from backend.core.config import settings
from backend.core.exceptions import AppError
from backend.core.limits import RateLimiter
from backend.core.notify import new_visitor
from db.database import connect, load_seed, migrate

log = logging.getLogger(__name__)

WORKSPACE_HEADER = "X-Workspace-ID"
_VALID = re.compile(r"^ws_[A-Za-z0-9_-]{16,64}$")
_create_lock = threading.Lock()


def workspace_from_request(request: Request) -> str | None:
    """The workspace ID for this request, or None for the default database.

    Raises INVALID_WORKSPACE (400) for a malformed ID, so it can never become a file path trick.
    """
    if not settings.workspaces:
        return None
    raw = request.headers.get(WORKSPACE_HEADER, "").strip()
    if not raw:
        return None
    if not _VALID.match(raw):
        raise AppError("INVALID_WORKSPACE", "The workspace ID is not valid.", 400)
    return raw


def database_path(workspace: str | None) -> str:
    if workspace is None:
        return settings.database_path
    return str(Path(settings.workspace_dir) / f"{workspace}.db")


def ensure_workspace(workspace: str, client_ip: str) -> None:
    """Create the workspace database with the demo data on first use (rate-limited per IP)."""
    path = Path(database_path(workspace))
    if path.exists():
        return
    with _create_lock:
        if path.exists():
            return
        if not workspace_limiter.allow(f"ip:{client_ip}"):
            raise AppError("RATE_LIMITED", "Too many new workspaces from this address. Try again later.", 429)
        conn = connect(path)
        try:
            migrate(conn)
            load_seed(conn)
        finally:
            conn.close()
        log.info("workspace created", extra={"event": "workspace.created", "workspace": workspace})
    new_visitor()


def workspace_databases() -> list[str]:
    """All workspace database files (used at startup to mark interrupted analyses)."""
    folder = Path(settings.workspace_dir)
    return sorted(str(p) for p in folder.glob("ws_*.db")) if settings.workspaces and folder.exists() else []


def client_ip(request: Request) -> str:
    """Caller address; behind the host's proxy the first X-Forwarded-For entry is the client."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


workspace_limiter = RateLimiter(limit=settings.max_new_workspaces_per_hour, window_seconds=3600)
analysis_limiter = RateLimiter(limit=settings.max_analyses_per_hour, window_seconds=3600)


def check_analysis_allowed(request: Request, workspace: str | None) -> None:
    """Protects the hosted model's free quota: a cap per caller address and per workspace.
    Only on the public deployment (WORKSPACES=true); local runs are not limited."""
    if not settings.workspaces:
        return
    keys = [f"ip:{client_ip(request)}"] + ([f"ws:{workspace}"] if workspace else [])
    if not all(analysis_limiter.allow(k) for k in keys):
        raise AppError("RATE_LIMITED", "Too many analyses in the last hour. Please try again later.", 429)
