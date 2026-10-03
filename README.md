# Contract Obligation and Renewal Assistant

Upload a contract (PDF/DOCX) and get structured, **cited**, human-reviewable data: parties,
dates, renewal and notice terms, obligations, and **deterministically calculated**
deadlines. Conflicting clauses are surfaced as clarification questions and never resolved
silently.

> Information-management tool. **Not legal advice.**

**Status:** working end-to-end MVP: upload → AI extraction with verified citations →
deterministic deadlines → human review. **Live demo: https://contract-assistant-flame.vercel.app**

- **AI evaluation:** 100% precision and 0 invented values on the 5 sample contracts ([results and caveats](docs/testing/ai-evaluation.md)).
- **Tests:** 144 backend/AI tests and 54 frontend tests, none of which need the model ([strategy](docs/testing/strategy.md)).
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
| `make test` | 144 backend/AI tests (pytest) + 54 frontend tests (Vitest) + frontend ESLint. No model needed |
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
Browser ── React + JavaScript (Vite) ──HTTP/JSON──▶ FastAPI ──▶ services ──▶ SQLite
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
| Frontend | React 18 (JavaScript/JSX), Vite, Tailwind, React Router; Node.js 18+ for tooling | `frontend/` |
| API and services | Python 3.11+, FastAPI, Uvicorn, Pydantic | `backend/` |
| Documents | PyMuPDF (PDF), python-docx (DOCX) | `backend/documents/` |
| Data | SQLite via built-in `sqlite3` (no ORM); schema in SQL migrations | `db/` |
| AI | Qwen3-8B via Ollama locally; Qwen (`qwen3.8-27b`) via Groq online; JSON Schema output, grounding validators | `ai/` |
| Dates | Pure functions with unit tests | `backend/utils/dates.py` |
| Tests and quality | pytest, Vitest + Testing Library, ruff, ESLint, Prettier | `tests/`, `frontend/src/**/*.test.*` |

Details: [architecture](docs/architecture/overview.md), [data flow](docs/architecture/data-flow.md),
[AI pipeline](docs/ai/pipeline.md), [prompt design](docs/ai/prompts.md), [API](docs/api/api-contract.md), [schema](docs/database/schema.md),
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
| Docker, job queue | Local: three processes. Online: free managed hosts (Vercel, Render, Groq). Analysis runs as a FastAPI background task |

Full list: [docs/product/scope.md](docs/product/scope.md).

## Tests

| Suite | Count | Covers |
|---|---|---|
| Backend (pytest) | 67 | date engine, parsers, API endpoints, errors and logging (request IDs, JSON log events) |
| AI (pytest) | 60 | citation validation, grounding, conflicts, clarification templates, Ollama and Groq clients (provider selection, rate-limit retries, errors, timeouts), evaluation metrics |
| Integration (pytest) | 17 | upload → analyze → review → recalculate; re-analysis; versions; edge cases |
| Frontend (Vitest) | 54 | API client errors, hooks, error states, form validation, review actions, conflict resolution, upload and contracts pages |
| AI evaluation (`make eval`; `LLM_PROVIDER=groq` for the hosted model) | 5 contracts | precision, invented values, missing information, conflicts, dates, citations against expected outputs |

The default suite uses a scripted fake model and never calls Ollama or Groq, so it runs in seconds offline. Model
quality is measured by `make eval`. Details: [testing strategy](docs/testing/strategy.md).

## Limitations
- **Accuracy is measured on 5 short synthetic contracts.** The results show the guards work; they do not prove accuracy on long, real-world contracts.
- **Speed:** about 1–2 minutes per contract locally on an Apple M1 Pro; about 20–75 seconds online with Groq, plus up to a minute if the free backend was asleep.
- **Text PDFs and DOCX only.** No OCR. PDF text blocks are read top to bottom, so a two-column layout can mix its columns; DOCX tables are read row by row.
- **Online demo:** data resets on every restart, and uploaded text goes to Groq (see Deployment).
- **Single user, single process.** No login. Analysis progress is held in memory, and a restart marks running analyses as failed (they can be re-run).
- **Date rules are simplified:** weekends only (no holidays), next due date only, no termination date calculation.
- **Manual-only checks:** the analysis progress page, the source drawer and the visual layout are tested by hand, not automatically.
- **Known dependency advisory:** `react-router-dom` 6.x has a moderate advisory (open redirect via crafted links). The app only links to IDs from its own backend. The breaking v7 upgrade is deferred.

## Deployment

**Live demo: https://contract-assistant-flame.vercel.app** (API: https://contract-assistant-api-4qba.onrender.com/docs)

| Part | Host (free tier) | Config |
|---|---|---|
| Frontend | **Vercel**, static build of `frontend/` | `frontend/vercel.json` (SPA routing); `VITE_API_BASE_URL` set in the Vercel project |
| Backend API | **Render** free web service | [`render.yaml`](render.yaml) blueprint; deploys automatically on every push to `main` |
| AI model | **Groq** free API, `qwen/qwen3.8-27b` (`LLM_PROVIDER=groq`) | `GROQ_API_KEY` set in the Render dashboard, never in git |

No free host can run Qwen3-8B (it needs about 16 GB of RAM), so the online copy uses Groq's
hosted Qwen model through the same pipeline, prompts, grounding checks and human review. Its
evaluation: 100% recall, 97.1% precision, 0 invented values ([results](docs/testing/ai-evaluation.md)).
A live analysis of the Acme sample took 21 s and produced the correct notice deadline.

What to know about the online demo:
- **First visit after a quiet period:** Render's free service sleeps after 15 minutes without traffic; the first request wakes it in about a minute.
- **Data resets:** Render's free disk is not persistent, so each restart reloads the demo data (Acme and Globex). Uploads are temporary.
- **Privacy:** contract text uploaded online is sent to Groq. Use only non-confidential documents such as `contracts/samples/`. Run locally (`make dev`, Ollama) to keep text on your machine.
- **Limits:** Groq's free tier allows about 8,000 tokens per minute and 1,000 requests per day; the client waits and retries when it hits the per-minute limit.

Local setup is unchanged: `make dev` runs Ollama, the backend and the frontend on your machine.
How each part is configured and redeployed: [docs/architecture/deployment.md](docs/architecture/deployment.md).

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
| `frontend/` | React + JavaScript app (Vite, Tailwind), tests next to the code |
| `contracts/` | Sample contracts + expected extractions for evaluation |
| `tests/` | Backend, AI, database and integration tests |
| `scripts/` | setup, reset, seed, run backend, evaluate AI |
| `uploads/`, `data/` | Runtime files (git-ignored) |

## License
[MIT](LICENSE)
