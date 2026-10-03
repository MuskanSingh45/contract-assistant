# Contract Obligation and Renewal Assistant

Upload a contract (PDF/DOCX) and get structured, **cited**, human-reviewable data: parties,
dates, renewal and notice terms, obligations, and **deterministically calculated**
deadlines. Conflicting clauses are surfaced as clarification questions and never resolved
silently.

> Information-management tool. **Not legal advice.**

**Status:** working end-to-end MVP: upload → AI extraction with verified citations →
deterministic deadlines → human review.

- **AI evaluation:** 100% precision and 0 invented values on the 5 sample contracts ([results and caveats](docs/testing/ai-evaluation.md)).
- **Tests:** 130 backend/AI tests and 54 frontend tests, none of which need the model ([strategy](docs/testing/strategy.md)).
- **How AI coding agents were used:** [AGENT_USAGE.md](AGENT_USAGE.md).

## Setup

Requires Python 3.11+, Node.js 18+, [Ollama](https://ollama.com) (macOS: the Ollama app) and
about 16 GB of RAM for the model.

```bash
make setup   # once: venv + deps, .env files, database with demo data, pulls qwen3:8b (~5 GB)
make dev     # starts Ollama if needed, backend :8000 and frontend :5173. Ctrl-C stops both
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

| Command | What it does |
|---|---|
| `make test` | 130 backend/AI tests (pytest) + 54 frontend tests (Vitest) + typecheck. No model needed |
| `make lint` | ruff lint/format check, ESLint, Prettier check (`make fmt` fixes) |
| `make eval` | real-model evaluation on the 5 sample contracts (about 7 min) |
| `make reset` | restore the demo data (Acme clean, Globex with an open conflict) |

Configuration is by environment variables. `make setup` copies [`.env.example`](.env.example)
to `.env`. The app needs no API keys or other secrets.

**Demo:** run `make reset`, then upload `contracts/samples/simple/acme-services-agreement.pdf`
and watch the analysis. Open the Globex contract, resolve the 90 vs 60 day notice conflict in
the Review Queue, and the notice deadline appears.

## Architecture

```
Browser ── React + TypeScript (Vite) ──HTTP/JSON──▶ FastAPI ──▶ services ──▶ SQLite
                                                       │
                                                       └─ background task ─▶ AI pipeline ─▶ Ollama (Qwen3-8B, local)
```

**AI extracts; code validates, calculates and decides.**

1. **Upload:** the file's type, signature and size are checked, the file is stored, and a contract version is created.
2. **Analyze** (background task, polled by the UI):
   - **Parse:** PDF/DOCX → page- and section-aware text segments.
   - **Extract:** per text window, the model returns JSON constrained by a JSON Schema (terms and obligations).
   - **Validate:** schema validation with one retry. Every value needs a verbatim quote that is found in the document, otherwise it is dropped. Business checks.
   - **Analyze:** deterministic conflict detection → clarification questions → date calculation (notice deadline, term roll-forward, next due date) → comparison with the previous version → **one transaction** saves everything, so a failure saves nothing.
3. **Review:** a person approves, edits or rejects each value, with the source quote beside it. Deadlines are recalculated, and the original AI value is kept for audit.

| Layer | Tech | Where |
|---|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind, React Router | `frontend/` |
| API and services | FastAPI, stdlib `sqlite3` (no ORM) | `backend/` |
| Data | SQLite; schema in SQL migrations | `db/` |
| AI | Ollama + Qwen3-8B, JSON Schema output, grounding validators | `ai/` |
| Dates | Pure functions with unit tests | `backend/utils/dates.py` |

Details: [architecture](docs/architecture/overview.md), [data flow](docs/architecture/data-flow.md),
[AI pipeline](docs/ai/pipeline.md), [API](docs/api/api-contract.md), [schema](docs/database/schema.md),
decisions in [ADRs 001–008](docs/decisions/).

## Scope

### Completed
- Upload PDF/DOCX (text-based) and new versions of a contract.
- AI extraction of parties, effective/expiration dates, initial term, renewal terms, notice period, termination summary and obligations (responsible party, frequency, due rule).
- A citation for every value (section, page, verified quote) and a source drawer.
- Confidence per value. Approve, edit or reject with history; the original AI value is never overwritten.
- Deterministic deadlines: notice deadline, current term end with roll-forward, next obligation due date, and business days.
- Conflicts and missing information become clarification questions that block the affected deadline until a person answers.
- Version comparison with the previous version; changed items are marked for re-review.
- Dashboard, contracts, obligations, renewals and review queue pages, with loading, empty, validation, success and failure states.
- Request IDs from server to UI, a rotating log file, optional JSON logs with AI-workflow events, and a real-model evaluation.

### Deliberately excluded
| Excluded | Why / instead |
|---|---|
| Authentication, users, roles | Single-user local tool for the MVP |
| OCR for scanned PDFs | Fails clearly with `NO_EXTRACTABLE_TEXT` |
| AI summaries and LLM-based conflict detection | Conflicts are detected by code, so they are predictable and testable ([ADR 007](docs/decisions/007-deterministic-conflicts-and-citations.md)) |
| Full PDF viewer | Source drawer shows the quoted text with section and page |
| Recurring obligation schedules, holiday calendars | Next due date only; business days skip weekends only |
| Email/calendar reminders | Out of scope |
| Copying reviews to a new version | New version items start pending; old reviews stay on their version |
| Docker, job queue | Three local processes and a FastAPI background task |

Full list: [docs/product/scope.md](docs/product/scope.md).

## Tests

| Suite | Count | Covers |
|---|---|---|
| Backend (pytest) | 66 | date engine, parsers, API endpoints, errors and logging |
| AI (pytest) | 47 | citation validation, grounding, conflicts, clarification templates, model client errors and timeouts, evaluation metrics |
| Integration (pytest) | 17 | upload → analyze → review → recalculate; re-analysis; versions; edge cases |
| Frontend (Vitest) | 54 | API client errors, hooks, error states, form validation, review actions, conflict resolution, upload and contracts pages |
| AI evaluation (`make eval`) | 5 contracts | precision, invented values, missing information, conflicts, dates, citations against expected outputs |

The default suite uses a scripted fake model, so it runs in seconds without Ollama. Model
quality is measured by `make eval`. Details: [testing strategy](docs/testing/strategy.md).

## Limitations
- **Accuracy is measured on 5 short synthetic contracts.** The results show the guards work; they do not prove accuracy on long, real-world contracts.
- **Speed:** about 1–2 minutes per contract on an Apple M1 Pro; slower on machines without a GPU.
- **Text PDFs and DOCX only.** No OCR. PDF text blocks are read top to bottom, so a two-column layout can mix its columns; DOCX tables are read row by row.
- **Single user, single process.** No login. Analysis progress is held in memory, and a restart marks running analyses as failed (they can be re-run).
- **Date rules are simplified:** weekends only (no holidays), next due date only, no termination date calculation.
- **Manual-only checks:** the analysis progress page, the source drawer and the visual layout are tested by hand, not automatically.
- **Known dependency advisory:** `react-router-dom` 6.x has a moderate advisory (open redirect via crafted links). The app only links to IDs from its own backend. The breaking v7 upgrade is deferred.

## Deployment

**Current state: runs locally only; not deployed online.** `make setup` and `make dev` start
the three processes:

| Process | Command | Port |
|---|---|---|
| Ollama + Qwen3-8B | `ollama serve` (native, not Docker: Docker on macOS has no GPU access) | 11434 |
| Backend | `uvicorn backend.main:app` | 8000 |
| Frontend | `npm run dev` in `frontend/` (production: `npm run build` → static `frontend/dist/`) | 5173 |

What a hosted deployment needs:
- **Frontend:** the static build from `npm run build`, with `VITE_API_BASE_URL` pointing at the backend.
- **Backend:** one Python process. Set `FRONTEND_ORIGIN` to the frontend's URL and keep `DATABASE_PATH`, `UPLOAD_DIR` and `LOG_FILE` on persistent storage.
- **Model:** an Ollama server with `qwen3:8b`, reachable through `OLLAMA_BASE_URL`. It needs about 16 GB of RAM, and a GPU for usable speed.

Hardware and configuration: [docs/architecture/deployment.md](docs/architecture/deployment.md).

## Logs and troubleshooting
The backend logs to the console and to `data/logs/backend.log` (rotating). Every line has the
request ID, and the UI shows the same ID as **Reference** on error screens:

```
2026-10-03 14:39:32,403 WARNING [req_82488e9c75c3] backend.access: GET /api/contracts/nope -> 404 (24 ms)
```

To trace a failure: `grep req_82488e9c75c3 data/logs/backend.log`. The trace includes the
background analysis started by that request. Set `LOG_LEVEL=DEBUG` in `.env` to also see
status polling, and `LOG_FORMAT=json` for one JSON object per line (events such as
`http.request`, `analysis.completed`, `llm.call` with token counts and durations). Details: [backend logging](docs/architecture/backend-architecture.md#logging).

| Symptom | Cause / fix |
|---|---|
| "Cannot reach the server" in the UI | Backend not running on :8000. Run `make dev` |
| Upload works but "AI model is unavailable" | Ollama not running or model not pulled: `ollama pull qwen3:8b`, then re-analyze |
| Analysis failed with `NO_EXTRACTABLE_TEXT` | Scanned PDF (OCR is out of scope) |
| Analysis failed after a restart | Runs interrupted by a restart are marked failed. Click re-analyze |

## Repository
| Path | Contents |
|---|---|
| `docs/` | Product, architecture, API, database, AI, frontend, ADRs, testing. **Start at [docs/README.md](docs/README.md).** |
| `AGENT_USAGE.md`, `.ai/` | How AI coding agents were used; their shared context, rules and task board |
| `backend/` | FastAPI app, services, document parsers, date engine |
| `ai/` | Ollama client, extraction pipeline, validators, prompts, JSON Schemas, evaluation |
| `db/` | SQL migrations (schema source of truth), seed data, connection/migration runner |
| `frontend/` | React + TypeScript app (Vite, Tailwind), tests next to the code |
| `contracts/` | Sample contracts + expected extractions for evaluation |
| `tests/` | Backend, AI, database and integration tests |
| `scripts/` | setup, reset, seed, run backend, evaluate AI |
| `uploads/`, `data/` | Runtime files (git-ignored) |

## License
[MIT](LICENSE)
