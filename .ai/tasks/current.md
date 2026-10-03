# Current Tasks

Status: `todo` · `in progress` · `done` · `blocked`. Pick only tasks whose dependencies are `done`.
Order = critical path to the demo. Tasks marked ⭐ are required for the demo.

| ID | ⭐ | Task | Owner | Depends | Status | Docs |
|---|---|---|---|---|---|---|
| T00 | ⭐ | Reconcile docs, schema, API spec, AI schemas, `.ai/` | Claude | — | done | `tasks/completed/2026-10-03-T00-docs-reconciliation.md` |
| F01 | ⭐ | Frontend built in-repo from the product designs (Lovable dropped): Claude did the foundation, contract detail, review queue and review item; Codex did dashboard, contracts, upload, analyzing, obligations, renewals, versions, summary | Claude + Codex | T00 | done | `docs/frontend/*`, `docs/api/*` |
| B01 | ⭐ | `db/database.py` connect + migrate runner; `scripts/setup.py`, `scripts/reset_dev.py`, `scripts/seed_db.py` | Codex | T00 | done | `docs/database/migrations.md` |
| B02 | ⭐ | FastAPI skeleton: config, AppError + handlers (incl. 422 → VALIDATION_ERROR), CORS, health, startup migrate + stale-analysis cleanup | Codex | B01 | done | `docs/architecture/backend-architecture.md`, `docs/api/errors.md` |
| B03 | ⭐ | Read endpoints over seed data: contracts list/detail, extracted-items, obligations, renewals, dashboard, citations, clarifications, versions, review queue | Codex | B02 | done | `docs/api/*` |
| B04 | ⭐ | `backend/utils/dates.py` + full unit tests (test-cases.md, Date calculation) | Codex | — | done | `docs/architecture/date-calculation.md` |
| B05 | ⭐ | Upload + new version endpoints (type/signature/size/hash checks, file storage) | Codex | B02 | done | `docs/api/contracts.md`, `docs/api/versions.md` |
| B06 | ⭐ | Parsers: PDF/DOCX/TXT → normalized segments (page, section) + tests | Codex | — | done | `docs/ai/pipeline.md` §1 |
| A01 | ⭐ | `ai/llm/`: Ollama client (`format`, `think=false`, `num_ctx`, timeout, availability check, context guard) | Claude | — | done | `docs/ai/model-config.md` |
| A02 | ⭐ | Citation + extraction + confidence validators + unit tests | Claude | — | done | `docs/ai/citation-and-review.md`, `docs/ai/confidence.md` |
| A03 | ⭐ | Orchestrator: windowing, terms + obligations extraction, retry, merge, conflict detection, clarification templates | Claude | A01, A02 | done | `docs/ai/pipeline.md`, `docs/ai/conflict-detection.md`, `docs/ai/clarification.md` |
| A04 | | `scripts/evaluate_ai.py` + metrics on Acme/Globex samples | Claude | A03, B04, B06 | done | `docs/testing/ai-evaluation.md` |
| B07 | ⭐ | Analysis service: background task, stages/progress, call orchestrator, date calc, one-transaction persist; analyze + analysis endpoints | Codex | B04, B05, B06, A03 | done | `docs/api/analysis.md`, `docs/architecture/data-flow.md` |
| B08 | ⭐ | Review + clarification resolve + obligation PATCH, with recalculation | Codex | B03, B04 | done | `docs/api/reviews.md`, `docs/api/clarifications.md` |
| F02 | ⭐ | Frontend wired to the real API (no mocks); verified in Chrome: upload, live analysis, conflict resolution, source drawer | Claude | | done | `docs/frontend/architecture.md` |
| B09 | | Version comparison (`version_changes`) + changes endpoint | Codex | B07 | done | `docs/api/versions.md` |
| T01 | | API + integration tests per `docs/testing/test-cases.md` | Codex | B08 | done | `docs/testing/*` |
| R01 | | Review B01–B09 against docs | Claude | each B task | done | `.ai/agents/reviewer.md` |
| S01 | | More samples: renewal (term length, business days), ambiguous, multiple-obligations | Claude | A04 | done | `contracts/README.md` |
| Q01 | | Error handling and logs: request IDs end to end, access log, log file, frontend error boundary, timeouts | Claude | — | done | `docs/architecture/backend-architecture.md#logging`, `docs/api/errors.md` |
| Q02 | | Frontend tests (Vitest + Testing Library) | Claude | — | done | `docs/testing/strategy.md#frontend` |
| Q03 | | Maintainability: ruff config + format, ESLint + Prettier, `make lint`, remove duplicated SQL | Claude | — | done | `ruff.toml`, `frontend/eslint.config.js` |
| Q04 | | Docs reconciled with the built app (Lovable/mocks removed); agent-use write-up | Claude | — | done | `AGENT_USAGE.md` |
| Q05 | | Structured logs: `LOG_FORMAT=json`, named events for HTTP, analysis and LLM steps | Claude sub-agent, reviewed by Claude | Q01 | done | `docs/architecture/backend-architecture.md#logging` |
| Q06 | | Client-side validation in the review edit and clarification answer forms | Claude sub-agent, reviewed by Claude | Q02 | done | `docs/frontend/architecture.md#error-handling` |
| Q07 | | README (architecture, scope, tests, limitations, deployment) and root `AGENT_USAGE.md` (prompts, mistakes, verification) | Claude | Q04 | done | `README.md`, `AGENT_USAGE.md` |
| Q08 | | Frontend converted from TypeScript to JavaScript (developer's stack choice); types kept as JSDoc typedefs | Claude | Q07 | done | `docs/decisions/008-frontend-language.md` |
| Q09 | | Hosted model provider (Groq) behind `LLM_PROVIDER`, rate-limit handling, evaluation on Groq | Claude | Q08 | done | `docs/ai/model-config.md` |
| P01 | | Git history, license, demo rehearsal | User | Q01–Q07 | in progress | history and MIT license pushed to github.com/MuskanSingh45/contract-assistant; demo rehearsal left |
| P02 | | Online deployment: frontend on Vercel, backend on Render, model on Groq (free tiers); live end-to-end analysis verified | Claude + developer (accounts) | P01 | done | `docs/architecture/deployment.md` |

**Status 2026-10-03 night:** the end-to-end demo works with the real model (about 2 min per contract). A04 (evaluation), S01 (3 more samples) and T01 (17 integration tests, by Codex) are done. Fixed a parser bug: short numbered clauses were dropped as headings (regression test added).

**Status 2026-10-03, quality pass (Q01–Q04):** `make test` passes (130 backend/AI + 54 frontend tests + frontend checks) and `make lint` is clean. Log: `tasks/completed/2026-10-03-Q01-Q04-quality-pass.md`. Q05–Q06 added JSON logs and form validation (log: `tasks/completed/2026-10-03-Q05-Q06-logs-validation.md`).

**Status 2026-10-03, night:** frontend converted to JavaScript (Q08), dead placeholders removed, Groq provider added (Q09), and the app deployed and verified live (P02; log: `tasks/completed/2026-10-03-Q08-Q09-P02-js-groq-deploy.md`). `make test`: 144 backend/AI + 54 frontend. Remaining: demo rehearsal (P01).

**Parallel start:** F01, B01, B04, B06, A01 and A02 have no blocking dependencies.
**Demo-safe fallback:** if AI work slips, B03 + F02 over seed data still demonstrate review, citations, conflicts and deadlines.

## Blocked / questions
None.
