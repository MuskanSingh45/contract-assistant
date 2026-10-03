# db/

| Path | Purpose |
|---|---|
| `migrations/NNN_*.sql` | **The only schema definition.** Applied in order and tracked in `schema_migrations`. |
| `seeds/development.sql` | Demo data (Acme: clean; Globex: notice-period conflict). Matches the examples in `docs/api/`. |
| `database.py` | `connect()` (foreign keys on, `sqlite3.Row`) and `migrate()` (applies pending migrations at startup) |

Quick manual check:
```bash
sqlite3 /tmp/check.db < db/migrations/001_initial.sql && sqlite3 /tmp/check.db < db/seeds/development.sql
```

Docs: `docs/database/`. Rules for changes: `docs/database/migrations.md`.
