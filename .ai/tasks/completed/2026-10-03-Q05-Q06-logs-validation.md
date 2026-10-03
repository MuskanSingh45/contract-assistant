# Q05–Q06: Structured logs, form validation (2026-10-03, two Claude sub-agents, reviewed by Claude)

Each was built by its own sub-agent in parallel, with no file overlap (backend vs frontend). Claude wrote the briefs, reviewed both diffs against the schemas and docs, re-ran every check, and updated the docs.

## Q05 Structured logs
- `LOG_FORMAT=json` (default `text`, unchanged): `JsonFormatter` in `backend/core/logging.py`, standard library only. Each record has `ts`, `level`, `logger`, `request_id`, `message`, `exc`, plus the call site's `extra=` fields.
- Events: `app.started`, `http.request`, `http.error`, `analysis.started|parsed|completed|failed|interrupted`, `llm.call`, `llm.retry`, `extraction.dropped`, `pipeline.finished`. Catalogued in `docs/architecture/backend-architecture.md#logging`.
- 5 new tests in `tests/backend/api/test_logging.py`. Checked on a live server.

## Q06 Client-side validation
- `frontend/src/components/review/validation.ts`: `validateEditValue()`, following `ai/schemas/*.json` and `review_service.py`. Responsible party stays optional because the schema allows null. Whitespace-only text counts as empty.
- `EditValueForm` shows messages under each field after it is touched or on Save, with `aria-invalid` and `aria-describedby`. `ReviewActions` and `ClarificationCard` do not call the API while the form is invalid.
- Tests: 8 validator tests and 4 component tests.

## Verified
`make test`: 130 backend/AI passed, 54 frontend passed, typecheck ok. `make lint`: clean.
