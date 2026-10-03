"""SQLite connection and migration runner. Schema lives only in db/migrations/*.sql."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
SEED_FILE = Path(__file__).parent / "seeds" / "development.sql"


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'").fetchone()
    if not exists:
        return set()
    return {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations in filename order. Returns the versions applied."""
    done = applied_migrations(conn)
    applied = []
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = file.stem
        if version in done:
            continue
        conn.executescript(file.read_text())
        # Migrations record themselves; guard in case one forgets.
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        conn.commit()
        applied.append(version)
    return applied


def load_seed(conn: sqlite3.Connection) -> None:
    conn.executescript(SEED_FILE.read_text())
    conn.commit()
