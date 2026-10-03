# Project Context: Contract Obligation and Renewal Assistant

## What it is
A local web app that turns an uploaded contract (PDF/DOCX) into reviewable, cited, structured
data. That data covers parties, dates, renewal and notice terms, obligations, and
**deterministically calculated** deadlines. A human approves, edits or rejects every AI result.
It is **not legal advice**.

## Stack
| Layer | Tech |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind 3 + React Router, built in-repo; Vitest for tests |
| Backend | Python 3.11+, FastAPI, stdlib `sqlite3` (no ORM) |
| DB | SQLite, `data/app.db`, schema in `db/migrations/` |
| Documents | PyMuPDF, python-docx |
| AI | Qwen3-8B via Ollama (native), JSON Schema constrained output |
| Dates | Python `datetime` + `dateutil`, in `backend/utils/dates.py` |

## Status (2026-10-03, end of day)
| Area | State |
|---|---|
| Docs, API spec, DB schema + seed, AI schemas + prompts, samples | ✅ consistent with the code |
| Backend, DB runner, parsers, AI pipeline, validators, date engine | ✅ working end to end with the real model |
| Frontend | ✅ built in-repo, wired to the real API, verified in Chrome |
| Tests and lint | ✅ `make test` (130 backend/AI + 54 frontend) and `make lint` pass |
| Error handling and logs | ✅ request IDs end to end, rotating log file ([backend logging](../docs/architecture/backend-architecture.md#logging)) |
| Git history, deployment packaging | 🟡 next (see `tasks/current.md`) |

## Non-negotiable rules
1. **AI extracts; code decides.** The LLM never does date arithmetic, never supplies page numbers, never picks between conflicting clauses, and never writes clarification text.
2. **No ungrounded data.** Every extracted item and obligation needs evidence (segment + verbatim quote). Candidates with no evidence are dropped. Unverifiable quotes force `confidence = low`.
3. **Missing means `[]`/`null`.** Never a default or a guess.
4. **Conflicts block, they don't resolve.** Different values for a single-valued field → clarification question + `blocked_by_conflict`.
5. **Confidence ≠ review status ≠ obligation status.** These are three separate fields.
6. **The original AI value is immutable.** Edits change `value`, never `original_value`.
7. **Versions are never overwritten.** Re-analysis replaces a version's analysis output but never its `reviews`.
8. **Failed analysis persists nothing partial,** and an unavailable model fails visibly (`AI_UNAVAILABLE`).
9. **The frontend never calculates dates.** It formats what the API returns.
10. **Documented contracts only.** Don't invent endpoints, fields or enum values. Add them to `docs/` first.

## Sources of truth
| Topic | File |
|---|---|
| DB schema | `db/migrations/*.sql` |
| API | `docs/api/` (start at `api-contract.md`) |
| LLM output | `ai/schemas/extraction.json`, `ai/schemas/obligation.json` |
| Date rules | `docs/architecture/date-calculation.md` |
| AI pipeline | `docs/ai/pipeline.md` |
| Demo data | `db/seeds/development.sql` (Acme = clean; Globex = conflict) |
| Decisions | `docs/decisions/` ADR 001–008 |

## Do NOT build (MVP)
Auth/users, OCR, Docker, cloud deploy, email/calendar, AI summarization, LLM-based conflict
detection, a PDF viewer, recurring obligation schedules, holiday calendars, analytics
dashboards, copying reviews forward across versions.

## Demo flow (what must work end to end)
Dashboard → Upload PDF → Analysis progress → Contract overview (notice deadline 2026-11-02 for
Acme) → Extracted info with confidence → View source drawer → Approve/Edit/Reject → Review
page: resolve Globex 90 vs 60 day conflict → deadline appears → upload v2 → see changes.
