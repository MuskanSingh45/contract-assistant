# Contract Obligation and Renewal Assistant

Upload a contract (PDF/DOCX) and get structured, **cited**, human-reviewable data: parties,
dates, renewal and notice terms, obligations, and **deterministically calculated**
deadlines. Conflicting clauses are surfaced as clarification questions and never resolved
silently.

> Information-management tool. **Not legal advice.**

## Architecture in one line
React + TypeScript → FastAPI → SQLite + AI pipeline → Ollama / Qwen3-8B (local).
**AI extracts; code validates, calculates, and decides.**

## Status
Working end-to-end MVP: upload → AI extraction with verified citations → deterministic deadlines → human review.

- **AI evaluation:** 100% precision and 0 invented values on the 5 sample contracts ([results and caveats](docs/testing/ai-evaluation.md)).
- **Tests:** 130 backend/AI and 54 frontend, none of which need the model ([strategy](docs/testing/strategy.md)).
- **Task board:** [.ai/tasks/current.md](.ai/tasks/current.md).

## Run locally

Requires Python 3.11+, Node.js 18+ and [Ollama](https://ollama.com) (macOS: the Ollama app).

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

Demo files to upload: `contracts/samples/*/*.pdf`.

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
| `.ai/` | Shared context, rules and task board for the coding agents ([how agents were used](docs/process/agent-use.md)) |
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
