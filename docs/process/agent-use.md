# How AI Coding Agents Were Used

This project was built in about one day by one developer working with AI coding agents. This page records how the agents were used, how their work was checked, and what was kept under human control. The working files are in [`.ai/`](../../.ai/README.md).

## Agents and roles

| Agent | Role | Owned paths (from `.ai/agents/`) |
|---|---|---|
| Claude (Claude Code) | Docs and contract reconciliation, AI pipeline, evaluation, frontend foundation and review screens, **reviewer** for all other work; reworked and completed the backend after reviewing Codex's first version | `ai/`, `contracts/`, `tests/ai/`, review of everything |
| Claude sub-agents | Bounded pieces, each with a written brief, run in parallel when the files did not overlap: date engine, document parsers, AI pipeline parts, structured JSON logs (Q05), form validation (Q06). The main Claude session reviewed each result and re-ran the tests before accepting it | as assigned per brief (e.g. backend-only or `frontend/`-only) |
| Codex | First implementation of backend tasks B01–B09, database runner, integration tests, half of the frontend pages | `backend/`, `db/`, `scripts/`, `tests/backend/`, `tests/integration/` |
| Lovable | Planned for the frontend; **dropped** because of the deadline ([ADR 008](../decisions/008-frontend-language.md)) | none |

No other agents were used.

The task board (`.ai/tasks/current.md`) records the owner of each task, and `.ai/tasks/completed/` has one log per finished piece of work.

## How the work was controlled

1. **Contracts before code.** Task T00 settled the docs first: one schema source (`db/migrations/`), API shapes (`docs/api/`), LLM output schemas (`ai/schemas/`) and the date rules. Agents were told to implement *exactly* these and to ask, not invent, when something was missing ([coding rules](../../.ai/coding-rules.md), rule 10 in [project context](../../.ai/project-context.md)).
2. **Shared context.** Every agent reads the same files before starting: project context with the non-negotiable rules, coding rules, its role file, and the task board.
3. **Owned paths.** Each role file lists the directories the agent may change. Changes outside them, or to a documented contract, go to *Blocked / questions* on the task board.
4. **Small, dependency-ordered tasks.** Each task links to the docs it implements, and the board marks the critical path to the demo (⭐).
5. **A written record.** Each finished task gets a log of what changed, how it was verified and what was left, so the next agent or person does not depend on chat history.

## How agent output was verified

Nothing was accepted on an agent's word alone:

| Check | Evidence |
|---|---|
| Automated tests | `make test`: 130 backend/AI tests and 54 frontend tests, plus the typecheck ([strategy](../testing/strategy.md)) |
| Lint / format | `make lint`: ruff, ESLint, Prettier |
| Cross-review | Claude reviewed Codex's backend (task R01) against the docs, using the [reviewer checklist](../../.ai/agents/reviewer.md), then changed it where it did not match: the analysis task, the review/clarification/version services, recalculation, and the documented additions (`/reviews/recent`, `/items/{type}/{id}`, extra fields). Claude also reviewed Codex's frontend pages and fixed about 15 issues (raw field names shown, wrong date sorting, wrong citations on Renewals) |
| AI quality | `make eval` on 5 sample contracts with expected outputs. The first run found 3 invented values and 1 right ("may inspect") turned into an obligation; deterministic checks were added and the second run had 0 of each ([results](../testing/ai-evaluation.md)) |
| Real usage | The demo flow was run in Chrome against the real backend and model: upload, live analysis, conflict resolution, source drawer (F02) |
| Regression tests | Bugs found during review got a test, e.g. the parser dropping short numbered clauses |

## What stayed with the human

- Scope, deadline and priorities: what is in the MVP and what is deliberately out (`docs/product/scope.md`).
- Architecture decisions, recorded as ADRs 001–008 for review.
- Dropping Lovable and building the frontend in the repo.
- Committing and publishing. Agents do not commit or push.
- The license and the final demo.

## Responsible AI inside the product

The same rule applies to the AI in the product as to the coding agents: **the model proposes, code and a person decide.**

- **AI extracts; code decides.** The model never does date arithmetic, never picks between conflicting clauses and never writes the questions shown to users ([ADR 007](../decisions/007-deterministic-conflicts-and-citations.md)).
- **Grounded or dropped.** Every value needs a verbatim quote that is found in the document. A value without supported evidence is discarded, and a quote that cannot be found forces low confidence.
- **Missing stays missing.** The model returns `[]` instead of guessing, and the evaluation checks for this.
- **A person reviews everything.** Every item can be approved, edited or rejected, the original AI value is kept, and conflicts block the deadline until a person resolves them.
- **Local model.** Qwen3-8B runs in Ollama on the user's machine, so contract text is not sent to a third-party AI service.
- **Not legal advice.** This is stated in the app (Help page) and in the docs.

## Data and secrets during development

- The sample contracts in `contracts/samples/` are synthetic and contain no real parties or confidential data.
- `.env`, `data/` (database and logs) and `uploads/` are git-ignored.

## Known limits

- The AI evaluation uses 5 short synthetic contracts. It shows that the guards work; it does not prove accuracy on long real contracts.
- The analysis progress polling, the source drawer and the visual layout are checked by hand, not by automated tests.
- `react-router-dom` 6.x has a moderate advisory (open redirect via crafted `<Link>` targets). The app only links to IDs returned by its own backend, so it is not exposed. The fix is the v7 upgrade, which is breaking and was deferred until after the MVP. The v7 behaviour flags are already turned on.
