# ADR 001 — Stack

## Decision
| Layer | Technology |
|---|---|
| Frontend | React 18 + **JavaScript** (JSX), Vite, Tailwind CSS, React Router; Node.js 18+ for tooling |
| Backend | **Python** 3.11+, FastAPI, Uvicorn, Pydantic |
| Database | SQLite via Python's built-in `sqlite3` (no ORM), SQL migrations |
| Document processing | PyMuPDF (PDF), python-docx (DOCX) |
| AI | Qwen3-8B via Ollama locally; `qwen/qwen3.8-27b` via Groq's free API for the online deployment (`LLM_PROVIDER`); JSON Schema-constrained output |
| Hosting (online) | Vercel (frontend), Render free web service (backend), Groq (model) |
| Tests and quality | pytest, Vitest + Testing Library, ruff, ESLint, Prettier |

The frontend was first written in TypeScript and converted to JavaScript at the developer's
request ([ADR 008](008-frontend-language.md)).

## Reason
Supports a local, lightweight prototype while keeping UI, application logic, persistence, and AI separated.
