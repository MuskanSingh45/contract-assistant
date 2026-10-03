# Q01–Q04: Error handling, frontend tests, maintainability, docs (2026-10-03, Claude)

## Why
A review against the grading criteria found these weak or unproven: error handling/logs (no request correlation, no log file), frontend testing (typecheck only), maintainability (no lint config, 40 ruff findings, no frontend lint), and docs that still described Lovable and a mock mode that does not exist.

## Q01 Error handling and logs
- `backend/core/logging.py`: `RequestContextMiddleware` (pure ASGI) assigns or reuses `X-Request-ID`, returns it on every response, and writes one access line per request with status and duration (4xx WARNING, 5xx ERROR, successful polling DEBUG). The request ID is on every log line through a contextvar, including background analysis.
- `LOG_LEVEL` and `LOG_FILE` settings (default `data/logs/backend.log`, rotating 5 MB × 3). Uvicorn's access log turned off.
- `backend/core/exceptions.py`: every error body includes `request_id`; each handled error is logged once; 405 → `METHOD_NOT_ALLOWED`; 500 responses carry the header.
- Analysis logs started, parsed and interrupted-on-restart events.
- Frontend: `ApiError.requestId`, 30 s timeout (`TIMEOUT`; uploads 120 s), console logging by severity, `errorMessage()` helper (fixed `VersionsTab` toasts showing "ApiError: …"), per-route `ErrorBoundary`, the error state shows the Reference and a title by code, accessible `ConfirmDialog` (role, label, Escape), React Router v7 future flags (removes console warnings).
- Tests: `tests/backend/api/test_logging.py` (9).

## Q02 Frontend tests
Vitest + Testing Library + jsdom; 42 tests in 9 files (API client, useApi, format, states, error boundary, clarification card, review actions, upload page, contracts page). `make test` runs them.

## Q03 Maintainability
- `ruff.toml` (E, W, F, I, B, BLE, UP, DTZ, RUF; FastAPI `Depends` etc. marked immutable), `ruff format` applied to the whole codebase (48 files, formatting only), and all findings fixed or documented.
- `version_counts()` in `backend/services/common.py` replaces the SQL that was copied in `contract_service` and `analysis_service`.
- Frontend ESLint (typescript-eslint + react-hooks) and Prettier; `make lint` and `make fmt`.
- `.gitignore`: `*.tsbuildinfo`. CORS: dropped the Lovable preview origins.

## Q04 Docs
README, `docs/frontend/*`, ADR 008, `docs/product/scope.md`, `docs/api/README.md`, `docs/api/errors.md` (request IDs, new codes, client-side codes), `docs/architecture/backend-architecture.md` (errors, logging, CORS), `docs/testing/strategy.md` (rewritten with real suites and counts), `.ai/*` (status, roster, rules), new `docs/process/agent-use.md`.

## Verified
`make test`: 125 passed (1 llm deselected), 42 frontend passed, typecheck ok. `make lint`: clean. A live uvicorn run confirmed the log format, the header and the file output.

## Follow-ups
- `react-router-dom` advisory (moderate). Not exploitable here; upgrade to v7 after the MVP.
- No automated test for the analysis progress polling or the source drawer.
- P01 git history and license, P02 deployment.
