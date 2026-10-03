# Database Architecture

SQLite file at `DATABASE_PATH` (default `data/app.db`), accessed with stdlib `sqlite3`.
Migrations in `db/migrations/` are the only schema source.

Full details are in [docs/database/](../database/schema.md). Relationships:
[docs/database/relationships.md](../database/relationships.md).

```text
Contract
 └── ContractVersion
      ├── DocumentSegment
      ├── ExtractedItem ── Citations, Reviews
      ├── Obligation ───── Citations, Reviews
      ├── ClarificationQuestion ── Citations, Options
      ├── Renewal (calculated)
      └── VersionChange
```
