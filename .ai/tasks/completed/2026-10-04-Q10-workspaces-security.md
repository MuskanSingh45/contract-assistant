# Q10: Per-browser workspaces, security review, Groq fallback (2026-10-04, Claude)

## Why
The live demo used one shared database: every visitor saw every upload and could change anyone's review decisions. The developer also asked for a security check, Groq as the main model online and as a fallback locally, and the Lovable name removed from AGENT_USAGE.md.

## Workspaces ([ADR 009](../../../docs/decisions/009-workspace-isolation.md))
- `backend/core/workspace.py`: `X-Workspace-ID` (format `ws_[A-Za-z0-9_-]{16,64}`, else 400 `INVALID_WORKSPACE`) selects `WORKSPACE_DIR/<id>.db`, created on first use with migrations + demo seed. `get_db` and the background analysis open that file. Startup marks interrupted runs failed in every workspace DB.
- `WORKSPACES=true` only in `render.yaml`; local runs unchanged (`data/app.db`).
- Frontend: `workspaceId()` in `src/lib/api.js` (localStorage, in-memory fallback) sent on every request; Settings shows the workspace and "Start a fresh workspace".

## Security
- History scan: no keys/tokens/private keys ever committed; no `.env`, DB, uploads or logs tracked.
- New: `UploadSizeLimitMiddleware` (reject by Content-Length before reading), rate limits on new workspaces (30/h per address) and analyses (20/h per address and per workspace) → 429 `RATE_LIMITED`.
- Documented the full control list in `docs/architecture/backend-architecture.md#security`.

## Model routing
`LLM_FALLBACK_PROVIDER` + `active_config()`: primary first, fallback only when the primary is unavailable (logged `llm.fallback`). Online: Groq primary, no fallback. Local: Ollama primary, optional Groq fallback. `/api/health` reports provider, primary, fallback.

## Also
`make reset`; Lovable removed from AGENT_USAGE.md (it remains in ADR 008 and the history files, which record the original plan).

## Verified
158 backend/AI tests (10 workspace isolation, 3 fallback, 1 production-path) and 56 frontend tests; ruff, ESLint, Prettier clean. Live isolation checked after deploy (see commit).
