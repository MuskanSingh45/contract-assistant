"""Per-request SQLite connection."""

import sqlite3
from collections.abc import Iterator

from backend.core.config import settings
from db.database import connect


def open_db() -> sqlite3.Connection:
    return connect(settings.database_path)


def get_db() -> Iterator[sqlite3.Connection]:
    conn = open_db()
    try:
        yield conn
    finally:
        conn.close()
