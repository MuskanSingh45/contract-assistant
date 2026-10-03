# Agent: Backend (Codex, then Claude)

Codex wrote the first implementation of B01–B09. Claude reviewed it against the docs (R01) and reworked and completed it.

**Owns:** `backend/`, `scripts/`, `tests/backend/`, `requirements.txt`.

**Read first:** `docs/architecture/backend-architecture.md`, `docs/architecture/data-flow.md`, `docs/architecture/date-calculation.md`, `docs/api/` (all), `docs/database/schema.md`, `.ai/coding-rules.md`.

**Must:**
- Implement endpoints exactly as documented. The OpenAPI output must match `docs/api/`.
- Put all date logic in `backend/utils/dates.py`, as pure functions with full unit tests (see `docs/testing/test-cases.md`, Date calculation).
- Use the documented error codes and shape. Map FastAPI 422 to `VALIDATION_ERROR`.
- Run analysis as a background task, update stage/status, and persist results in one transaction.
- Call the `ai/` package through its orchestrator interface only.

**Must not:** call the LLM from anything but `ai/`, put SQL in `backend/api/`, edit `db/migrations/001_initial.sql` after it is merged (add `002_...` instead), or add an ORM.
