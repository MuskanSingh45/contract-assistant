# Agent: Database (Codex)

**Owns:** `db/`, `tests/database/`.

**Read first:** `docs/database/` (all), `db/migrations/001_initial.sql`, `db/seeds/development.sql`.

**Must:**
- `db/database.py`: `connect()` (sets `PRAGMA foreign_keys = ON`, `row_factory = sqlite3.Row`) and `migrate()` (applies pending `db/migrations/*.sql` tracked in `schema_migrations`).
- Keep `db/seeds/development.sql` loadable after every migration, and keep it consistent with the examples in `docs/api/`.
- Make schema changes as new numbered migrations, and update `docs/database/schema.md` in the same change.

**Must not:** reintroduce `db/schema/*.sql` or ORM models, or treat `data/app.db` as a source of truth.
