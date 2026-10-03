# Coding Rules

## General
- Match the documented contract exactly: names, enums and shapes from `docs/api/`, `db/migrations/` and `ai/schemas/`.
- Do not add dependencies not in `requirements.txt` / `package.json` without noting it in the task log.
- No dead code, no speculative abstractions, no placeholder implementations that return fake data. If something is not built, do not create a file for it.
- Keep functions small and pure where possible. Inject I/O (`today`, DB connection, LLM client).

## Python (backend/, ai/, db/, scripts/)
- Python 3.11+, type hints on public functions, run from the repo root (`backend`, `ai`, `db` are packages).
- Formatting/linting: `ruff format` + `ruff check`.
- SQL: parameterized queries only (`?`). Never use string formatting with values. Set `PRAGMA foreign_keys = ON` on every connection.
- One transaction per user action. Analysis results are written in one transaction at the end.
- IDs: `f"{prefix}_{uuid4().hex}"`. Timestamps: UTC ISO with `Z`. Dates: `date.isoformat()`.
- Errors: raise `AppError(code, message, status, details)` from `backend/core/exceptions.py` with codes from `docs/api/errors.md` only.
- All date arithmetic lives in `backend/utils/dates.py`. Nothing else may compute dates.
- `ai/` must not import from `backend/` or touch the DB. `backend/api/` must not contain SQL or call `ai/`.
- Logging: `logging.getLogger(__name__)`, never print. Never log full contract text or raw model responses. Request IDs are added automatically (`backend/core/logging.py`); do not add them by hand.
- Config only via `backend/core/config.py` (env vars from `.env.example`).

## Frontend
- JavaScript (`.js`/`.jsx`), no TypeScript. One API module (`src/lib/api.js`). Data shapes mirror `docs/api/` as JSDoc typedefs in `src/lib/types.js`.
- No date math. Use the API's `days_until_*` and calculated dates.
- Handle every documented error `code` the page can receive. Turn errors into text with `errorMessage(e)`, never `String(e)`. Page loads go through `Async`/`ErrorState`.
- Formatting/linting: Prettier + ESLint (`make lint`).

## Tests
- Run `make test` and `make lint` before marking a task done.
- `pytest`, files mirror source paths under `tests/`.
- Frontend: Vitest + Testing Library, `*.test.js(x)` next to the code. Query by role/label/text; stub `api.*`, not the network internals.
- Date and citation logic: pure unit tests with fixed `today = date(2026, 10, 3)`.
- Tests that need Ollama are marked `@pytest.mark.llm` and are skipped by default.
- API tests use a temporary SQLite file with migrations + seed applied.

## Docs
- A change that alters an API shape, the schema, an enum, or a rule updates the matching doc **in the same change**.
