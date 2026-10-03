# Backend Architecture

## Stack
Python 3.11+, FastAPI, Uvicorn, Pydantic, stdlib `sqlite3`, PyMuPDF, python-docx,
python-dateutil, httpx (Ollama client), jsonschema, rapidfuzz, python-dotenv. Tests: pytest;
lint/format: ruff. See `requirements.txt`.

## Layout

Run from the repo root (`uvicorn backend.main:app`). `backend`, `ai` and `db` are
top-level packages.

```text
backend/
├── main.py            FastAPI app, routers, CORS, error handlers, runs migrations on startup
├── api/               HTTP only: parse request → call service → return schema. No business logic.
│   ├── contracts.py       /contracts, /contracts/{id}, /extracted-items, /dashboard
│   ├── analysis.py        /analyze, /analysis
│   ├── versions.py        /versions, /changes
│   ├── obligations.py     /obligations, /renewals
│   ├── reviews.py         /reviews, /reviews/queue, /clarifications, /citations
│   └── health.py
├── services/          Workflows and SQL. One transaction per user action.
│   ├── contract_service.py      contracts, versions, uploads, derived summaries
│   ├── document_service.py      file storage, hashing, calls documents/ parsers
│   ├── analysis_service.py      runs the analysis: parse → ai/ → validate → calculate → persist
│   ├── obligation_service.py
│   ├── review_service.py        reviews, clarifications, triggers recalculation
│   └── version_service.py       version comparison
├── documents/         Parsing: file → normalized segments (no AI, no DB)
│   ├── parser.py          dispatch by type
│   ├── pdf_parser.py      PyMuPDF, per page
│   ├── docx_parser.py     python-docx, paragraphs/headings, page = None
│   ├── text_parser.py     .txt (evaluation/dev only, not exposed by upload)
│   └── normalizer.py      whitespace/quote normalization, heading detection, segmentation
├── schemas/           Pydantic request models where FastAPI validates the body (analysis, reviews); must match docs/api/
├── core/              config (env), exceptions (AppError → error shape), logging, dependencies (db connection)
└── utils/
    ├── dates.py           ALL date calculation (docs/architecture/date-calculation.md)
    ├── hashing.py         sha256 of uploads
    └── text.py            re-exports ai/text.py helpers (ai/ cannot import backend/)
```

`api/reviews.py` is a new file. It hosts reviews, clarifications and citations together to
keep the file count low. `/dashboard` and `/renewals` live in existing routers for the same
reason.

## Boundaries

- `api/` never touches SQL or calls `ai/` directly.
- `ai/` never touches the database or the filesystem beyond reading prompts and schemas. It receives segments and returns validated Python dicts.
- `utils/dates.py` is pure: no I/O, `today` is passed in.
- Analysis runs via FastAPI `BackgroundTasks`. Status and stage are written to `contract_versions` at each stage transition. Results are written in **one transaction at the end**, so a failure leaves nothing partial.
- On startup, any version left in `queued`/`processing` (server restarted mid-analysis) is marked `failed` with `ANALYSIS_FAILED` "Interrupted by server restart".

## Errors
Services raise `AppError(code, message, http_status, details)`. Handlers in
`backend/core/exceptions.py` convert every error to the documented shape, including
FastAPI's `RequestValidationError` (`VALIDATION_ERROR`), unknown routes (`NOT_FOUND`), wrong
methods (`METHOD_NOT_ALLOWED`) and any unexpected exception (`INTERNAL_ERROR`, generic message,
full traceback in the log). Each error body carries the `request_id`. See [../api/errors.md](../api/errors.md).

Analysis runs in the background, so its failures cannot be HTTP errors. They are classified
into the analysis failure codes, stored on the version (`analysis_error_code/message`) and
shown by the progress page. Nothing partial is persisted (one transaction). An analysis
interrupted by a server restart is marked failed on the next startup.

## Logging
`backend/core/logging.py`. One format for every line:

```
2026-10-03 14:39:32,403 WARNING [req_82488e9c75c3] backend.access: GET /api/contracts/nope -> 404 (24 ms)
```

- **Request ID** in brackets: from `RequestContextMiddleware`, also returned as `X-Request-ID` and in error bodies. Background analysis inherits the ID of the `POST /analyze` that started it, so one ID covers upload → analysis → failure. `-` means outside a request (startup).
- **Access line** per request (`backend.access`) with status and duration: INFO for 2xx/3xx, WARNING for 4xx, ERROR for 5xx. Successful polling of `/analysis` and `/health` is DEBUG so it does not flood the log. Uvicorn's own access log is turned off.
- **Error line** per handled error (`CODE (status): message`); a traceback for `INTERNAL_ERROR` and `ANALYSIS_FAILED`.
- **Analysis lifecycle**: started, parsed (segments/pages), each model call (`ai.llm`), dropped candidates and retries (`ai.pipeline`), completed (duration and stats) or failed (code).
- **Structured (JSON) mode**: `LOG_FORMAT=json` writes one JSON object per line instead, with `ts` (UTC ISO 8601), `level`, `logger`, `request_id`, `message`, `exc` (traceback, when present) and the event fields below. Text mode (default) prints the same messages. Uvicorn's own startup lines stay plain text.
- **Outputs**: console, plus a rotating file at `LOG_FILE` (default `data/logs/backend.log`, 5 MB × 3, git-ignored). `LOG_FILE=` (empty) disables the file. `LOG_LEVEL` defaults to `INFO`; `DEBUG` adds the polling lines.
- Full contract text and raw model responses are not logged. Logged: IDs, file names, counts, durations, error messages, and the field + value of a candidate the grounding checks dropped (to debug extraction).

Events (`event` field in JSON mode):

| Event | Fields | Logger |
|---|---|---|
| `app.started` | | `backend.main` |
| `http.request` | `method`, `path`, `status`, `duration_ms` | `backend.access` |
| `http.error` | `error_code`, `status` | `backend.core.exceptions` |
| `analysis.started` / `analysis.parsed` | `version_id`; `segments`, `pages` | `backend.services.analysis_service` |
| `analysis.completed` / `analysis.failed` | `version_id`, `duration_s`; `stats` or `error_code` | same |
| `analysis.interrupted` | `count` (runs failed by a restart) | same |
| `llm.call` | `model`, `prompt_tokens`, `output_tokens`, `duration_s` | `ai.llm.ollama_client` |
| `llm.retry` | (output failed schema validation; retried once) | `ai.llm.structured_output` |
| `extraction.dropped` | `reason` (`unsupported_evidence`, `invalid_value`, `not_supported_by_quotes`), `field` | `ai.pipeline.extraction` |
| `pipeline.finished` | `stats` | `ai.pipeline.orchestrator` |

Example (JSON mode): one AI run for a request, filtered with `jq`:

```bash
jq -c 'select(.request_id=="req_4867b604f76e") | {ts, event, status, error_code, duration_s}' data/logs/backend.log
```

Debugging a failure: take the **Reference** shown in the UI (or the `X-Request-ID` header) and run `grep req_xxx data/logs/backend.log`.

## CORS
Allow `FRONTEND_ORIGIN` (default `http://localhost:5173,http://localhost:8080`) and any
`localhost`/`127.0.0.1` port. `X-Request-ID` is exposed to the browser.
