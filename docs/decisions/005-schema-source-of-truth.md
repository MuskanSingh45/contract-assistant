# ADR 005 — Schema Source of Truth and Data Access

## Status
Accepted (2026-10-03).

## Context
The planned tree defined the schema in three places: `db/schema/*.sql`, `db/migrations/`
and `backend/models/`. Three definitions will drift apart, especially with several agents
editing.

## Decision
- `db/migrations/NNN_*.sql` is the only schema definition. `db/schema/` is removed.
- No ORM. The backend uses stdlib `sqlite3`. `backend/models/` holds plain dataclasses that mirror rows, for typing only.
- `backend/schemas/` (Pydantic) defines API request/response shapes. These must match `docs/api/`.
- `ai/schemas/*.json` defines the LLM output shape (JSON Schema passed to Ollama `format`). It is an internal contract between `ai/` and `backend/`, not an API shape.

## Update (2026-10-03)
`backend/models/` was never needed: services work with `sqlite3.Row` and serialize to the
`docs/api/` shapes directly. The empty placeholder package was removed, as were the
`backend/schemas/` modules that no endpoint used. `backend/schemas/` now holds only the
Pydantic request models that FastAPI validates (`analysis.py`, `review.py`).

## Consequences
SQL is written by hand in services, which is acceptable for about 12 tables. Any schema
change must update the migration, `docs/database/schema.md` and the affected API docs
together.
