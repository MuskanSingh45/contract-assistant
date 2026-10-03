# Q08, Q09, P02: JavaScript frontend, hosted model, live deployment (2026-10-03, Claude + developer)

## Q08 Frontend TypeScript → JavaScript (developer's stack choice)
Types removed with Sucrase (behaviour unchanged); API shapes kept as JSDoc typedefs in `src/lib/types.js`; configs moved to `.js`, `jsconfig.json`, ESLint for JS. A browser check caught an unstyled app (Tailwind still scanned `.ts/.tsx`); fixed. All 54 frontend tests pass.

## Cleanup
Removed `backend/models/` (8 empty files), four unused `backend/schemas` modules, empty folders and redundant `.gitkeep`s. Docs that described them were corrected. Every doc now states the same stack (ADR 001 table).

## Q09 Hosted model provider
No free host can run Qwen3-8B, and Hugging Face Docker Spaces now need a paid plan (HTTP 402). Added `LLM_PROVIDER` (`ollama` default, `groq` online) behind `make_client()`/`check_available()`; `ai/llm/groq_client.py` (OpenAI-compatible, non-strict `json_schema`, waits on 429 via `retry-after`, 2,500-token windows). `/api/health` now reports `llm {provider, model, reachable, model_available}`. 13 new tests. Evaluation on Groq `qwen/qwen3.8-27b`: 100% recall, 97.1% precision, 0 invented values (one real inspection-notice clause scored as unexpected).

## P02 Deployment
- Frontend: Vercel, https://contract-assistant-flame.vercel.app (`frontend/vercel.json`, `VITE_API_BASE_URL` in the project).
- Backend: Render free web service from `render.yaml`, https://contract-assistant-api-4qba.onrender.com; reloads demo data on each start.
- Model: Groq free API; the key was entered by the developer in `.env` and Render, never handled in chat or git.

## Verified
Live health OK (Groq reachable), CORS for the Vercel origin, live analysis of the Acme sample in 21 s with notice deadline 2026-11-02. `make test` 144 + 54, `make lint` clean, all doc links resolve.

## Follow-ups
Demo rehearsal (developer). Optional: laptop fast path (Ollama first, Groq fallback); CI workflow.
