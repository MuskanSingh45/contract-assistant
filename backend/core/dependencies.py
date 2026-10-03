"""Per-request SQLite connection, scoped to the caller's workspace (backend/core/workspace.py)."""

import sqlite3
from collections.abc import Iterator

from fastapi import Request

from backend.core.workspace import client_ip, database_path, ensure_workspace, workspace_from_request
from db.database import connect


def open_db(workspace: str | None = None) -> sqlite3.Connection:
    return connect(database_path(workspace))


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    workspace = workspace_from_request(request)
    if workspace:
        ensure_workspace(workspace, client_ip(request))
    conn = open_db(workspace)
    try:
        yield conn
    finally:
        conn.close()
