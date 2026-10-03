# T00: Docs / Structure Reconciliation (2026-10-03, Claude)

## Why
The docs were outlines with contradictions: three schema sources, `document_version_id` vs
`contract_version_id`, citations as both one-per-item and polymorphic, no
clarification table, renewals duplicated with extracted items, an analysis route without
`:id`, 4 API statuses vs 6 UI stages, missing endpoints (renewals, review queue,
dashboard, citations, clarifications, version changes), and an ambiguous
`POST /reviews/{item_id}`.

## What changed
- **Schema:** `db/migrations/001_initial.sql` (single source; `db/schema/` removed). Added document_segments, clarification_questions/options, version_changes; structured notice period; due rules; `origin`; analysis stage/error/model/prompt version.
- **Seed:** `db/seeds/development.sql` with Acme (clean, deadline 2026-11-02) and Globex (90 vs 60 day conflict). Verified: loads, FK check clean, citation offsets match.
- **API docs:** new `contracts.md`, `renewals.md`, `reviews.md`, `clarifications.md`, `citations.md`, `dashboard.md`. Rewrote `api-contract.md` (conventions + index), analysis, obligations, versions, errors.
- **Rules:** new `docs/architecture/date-calculation.md`. ADRs 005–008.
- **AI:** pipeline, extraction, citations, confidence, conflicts, clarification and model config rewritten. `ai/schemas/extraction.json` + `obligation.json` (validated against a sample response). Prompts `terms.txt` + `obligations.txt`.
- **Frontend docs:** route `/contracts/:id/analyzing`, data source per page, clarification/versions UI.
- **Samples:** Acme + Globex `.txt` with expected extractions.
- **Structure:** git init; `__init__.py` in backend/ai/db packages; `.gitkeep` in empty dirs; `backend/api/reviews.py` added; `requirements.txt`, `.env.example`, root `README.md`, `db/README.md`, `ai/README.md`, `contracts/README.md` written; `docs/ai/project-context.md` moved to `.ai/project-context.md`.
- **Removed (empty placeholders for deferred features):** summary prompt/schema/pipeline, analysis prompts, parties/dates/clauses prompts, conflict/clarification JSON schemas, `docker-compose.yml`, `scripts/run_frontend.py`, `scripts/run_ai.py`, empty `data/app.db`.

## Decisions taken (review if you disagree)
- No ORM; stdlib `sqlite3`.
- Conflicts and clarifications are deterministic (no extra LLM calls). Summarization is deferred.
- Renewals are calculated from extracted items and never reviewed directly.
- Termination clauses: summary text only.
- Notice conflicts are grouped by `anchor`, not `purpose`.
- Unreviewed items still feed calculations, flagged with `inputs_reviewed`.

## Not done
No application code. `frontend/` still holds the empty `.jsx` placeholders until the Lovable export lands. `LICENSE` is still empty.
