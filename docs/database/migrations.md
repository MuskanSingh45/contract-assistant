# Migrations

`db/migrations/` is the **only** place where schema DDL lives. There is no `db/schema/`
directory and no ORM model metadata. `backend/models/` holds plain dataclasses that mirror
rows; they do not define tables.

## Files

```text
db/migrations/
  001_initial.sql
  002_<short_name>.sql   ← next change
```

## Runner

`db/database.py` applies, in filename order, every migration whose version (filename
without `.sql`) is not yet in `schema_migrations`. It runs at backend startup and from
`scripts/setup.py`.

## Rules for a schema change

1. Add a new numbered file. Never edit a migration that has already been applied. (While nothing is deployed, `001_initial.sql` may be edited until the first backend PR merges; after that it is frozen.)
2. End it with `INSERT INTO schema_migrations ...`.
3. Prefer additive changes. SQLite cannot drop or alter columns easily, so destructive changes need an explicit table rebuild.
4. Update [schema.md](schema.md) and the affected `docs/api/*.md` in the same change.
5. Update `db/seeds/development.sql` if it no longer applies.

## Dev reset

`scripts/reset_dev.py` deletes `data/app.db`, re-applies migrations and loads the seed.
`data/app.db` is a runtime artifact (git-ignored) and is never the schema source.
