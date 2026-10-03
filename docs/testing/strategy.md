# Testing Strategy

| Command | Runs | Needs the model |
|---|---|---|
| `make test` | backend + AI tests (pytest, 144), frontend tests (Vitest, 54), frontend ESLint | no |
| `make lint` | ruff lint + format check, ESLint, Prettier check | no |
| `make eval` | real-model evaluation on the 5 sample contracts ([ai-evaluation.md](ai-evaluation.md)) | yes, about 7 min |
| `.venv/bin/python -m pytest -m llm` | the one live-model smoke test (deselected by default) | yes |

The default suite never calls Ollama or Groq (it is pinned to `LLM_PROVIDER=ollama` and mocks the network): AI tests use a scripted fake model (`tests/ai/fake_llm.py`), and API/integration tests replace the orchestrator. That keeps `make test` fast (a few seconds) and deterministic. Model quality is measured separately by `make eval`.

Concrete cases and their expected values are in [test-cases.md](test-cases.md). Reference "today" for date tests is **2026-10-03**.

## Backend and AI (pytest)

| Area | Location | Tests | What it proves |
|---|---|---|---|
| Date calculation | `tests/backend/services/test_dates.py` | 23 | notice deadlines, month clamping, business days, roll-forward, conflicts block deadlines |
| Parsing | `tests/backend/documents/` | 17 | PDF/DOCX/TXT → segments with page and section; empty/scanned files fail with the right code |
| API | `tests/backend/api/test_api.py` | 12 | endpoint shapes over the demo seed, upload checks, review/resolve recalculation, analysis failure persists nothing |
| Errors and logs | `tests/backend/api/test_logging.py` | 15 | every response has `X-Request-ID`; error bodies carry it; 500s are generic but logged with a traceback; background analysis logs carry the request ID of `POST /analyze`; log setup is idempotent; JSON mode emits parseable records with event fields and tracebacks; the bare server URL points to the API docs |
| AI | `tests/ai/` | 60 | citation validation, grounding checks (invented values dropped), conflict detection, clarification templates, Ollama client errors/timeouts, Groq client (provider selection, request shape, rate-limit waits, errors, health check), evaluation metrics |
| Integration | `tests/integration/` | 17 | upload → analyze → review → recalculate; re-analysis; version comparison; edge cases (empty text, duplicates) |

## Frontend

Vitest + Testing Library + jsdom. Run `npm test` in `frontend/` (or `npm run test:watch`). Tests sit next to the code.

| File | Tests | What it proves |
|---|---|---|
| `src/lib/api.test.js` | 10 | URL/query building, JSON and multipart bodies, error body → `ApiError` with request ID, non-JSON 5xx, network error, timeout |
| `src/lib/useApi.test.jsx` | 4 | loading → data, errors normalized to `ApiError`, reload clears errors, late responses ignored |
| `src/lib/format.test.js` | 5 | date display without timezone shift, days-until wording, citation labels, units |
| `src/components/ui/States.test.jsx` | 4 | error state shows title by code, message, reference and retry; stale data kept on failed reload |
| `src/components/ErrorBoundary.test.jsx` | 2 | a crashing page shows a recoverable message and is logged |
| `src/components/review/validation.test.js` | 8 | field rules for every editable value type (required, whole numbers above 0, real dates, enums, length limits) |
| `src/components/review/ClarificationCard.test.jsx` | 6 | conflicts show both cited values and never pre-select; resolve sends the chosen source + note; failure is shown inline; invalid answers are not sent |
| `src/components/review/ReviewActions.test.jsx` | 7 | approve, reject with confirmation (Escape cancels), edit sends the corrected value, invalid edits show inline messages and are not sent, failures keep the dialog open |
| `src/pages/UploadContract.test.jsx` | 5 | client-side type/size checks, upload → analyze → progress page, AI unavailable, server rejection |
| `src/pages/Contracts.test.jsx` | 3 | status per contract, search across parties, backend-down error with working retry |

Approach: tests interact the way a user does (roles, labels, visible text) and stub the `api` module or `fetch`, so they do not need the backend. `src/test/render.jsx` renders with the same providers as `main.jsx`; `src/test/fixtures.js` builds objects in the `docs/api/` shapes.

Not covered by automated tests: the analysis progress page's polling, the source drawer, and visual layout. These were checked by hand in Chrome against the running app (`.ai/tasks/current.md`, F02).

## Rules
- A bug fix comes with a regression test (example: the parser dropping short numbered clauses, `tests/backend/documents/`).
- A change to a prompt, schema, model or validator needs `make eval`; it is not merged if `hallucinated_values` or `rights_as_obligations` goes up.
- `make test` and `make lint` must pass before a task is marked `done` in `.ai/tasks/current.md`.
