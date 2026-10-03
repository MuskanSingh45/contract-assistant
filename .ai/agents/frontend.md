# Agent: Frontend (Claude + Codex)

Lovable was planned for this role and dropped ([ADR 008](../../docs/decisions/008-frontend-language.md)). The frontend is built in this repo.

**Owns:** `frontend/`.

**Read first:** `docs/frontend/architecture.md` (routes, API layer, error handling, testing), `docs/frontend/pages.md`, `docs/api/` (all files), `docs/product/user-flows.md`.

**Must:**
- Use the routes in `docs/frontend/architecture.md`, including `/contracts/:id/analyzing`.
- Keep all API calls in `src/lib/api.ts`, with types in `src/lib/types.ts` matching `docs/api/` exactly.
- Show confidence, review status and obligation status as three different badges.
- Show loading, empty and error states on every page; error states show the request ID (Reference).
- Add or update Vitest tests for changed behaviour; `make test` and `make lint` must pass.

**Must not:** calculate dates or `days_until`, invent endpoints or fields, or build auth or analytics pages.

**When something is missing from the API docs:** ask in `.ai/tasks/current.md` instead of inventing it.
