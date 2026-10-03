# AI Agent Usage

This project was built in about one day (2026-10-03, due 2026-10-04) by one developer working
with AI coding agents. This file records which tools were used, what was delegated, what
the prompts looked like, where the agents were wrong, and how every result was checked.
The agents' working files (shared context, rules, task board, task logs) are in [`.ai/`](.ai/README.md).

## Tools

| Tool | Used for |
|---|---|
| **Claude Code** (Claude, main session) | Docs and contract reconciliation, AI pipeline, evaluation, frontend foundation and review screens, reviewing all other agents' work, reworking the backend, quality pass (errors and logs, tests, lint, docs), git history |
| **Claude sub-agents** (spawned by Claude Code) | Bounded tasks with a written brief: date engine, document parsers, parts of the AI pipeline, JSON logs, form validation |
| **Codex** | First implementation of backend tasks B01–B09, database runner, integration tests, half of the frontend pages |
| Lovable | Planned for the frontend; **dropped** because of the deadline ([ADR 008](docs/decisions/008-frontend-language.md)) |

No other AI tools were used. The product itself uses a local model (Qwen3-8B via Ollama); that is part of the application, not a coding tool.

## How the work was organised

1. **Contracts before code.** The first task (T00) settled the docs: one schema source (`db/migrations/`), API shapes (`docs/api/`), LLM output schemas (`ai/schemas/`) and the date rules. Agents had to implement exactly these and ask, not invent, when something was missing.
2. **Shared context.** Every agent read the same files first: [project context](.ai/project-context.md) (with 10 non-negotiable rules), [coding rules](.ai/coding-rules.md), its role file in [`.ai/agents/`](.ai/agents/) and the [task board](.ai/tasks/current.md).
3. **Owned paths.** Each role file lists the directories that agent may change. Two agents never worked on the same files at the same time.
4. **Small tasks, written record.** Each task links to the docs it implements. Each finished task has a log in [`.ai/tasks/completed/`](.ai/tasks/completed/): what changed, how it was verified, what was left.

## Delegated work

| Work | Delegated to | Checked by | Outcome |
|---|---|---|---|
| Backend API and services (B01–B09) | Codex | Claude (review R01 against the docs) | Reworked by Claude where it did not match: the analysis task, the review/clarification/version services, recalculation |
| Database runner, seed scripts (B01) | Codex | Claude | Accepted |
| Integration tests (T01, 17 tests) | Codex | Claude | Accepted |
| Frontend pages: dashboard, contracts, upload, analyzing, obligations, renewals, versions, summary, settings, help | Codex | Claude | About 15 issues fixed (see mistakes below) |
| Date engine + 23 tests | Claude sub-agent | Claude | Accepted |
| PDF/DOCX/TXT parsers + tests | Claude sub-agent | Claude | Accepted; a bug found later (see below) |
| JSON log format with named events (Q05) | Claude sub-agent | Claude: diff review, full test run, live server check | Accepted |
| Client-side form validation (Q06) | Claude sub-agent | Claude: rules cross-checked against `ai/schemas/`, full test run | Accepted, with one deviation from the brief that was correct |
| Product scope, deadline, architecture decisions, dropping Lovable, license, GitHub account | **Not delegated:** the developer | — | — |

## Representative prompts

Prompts from the main session and the briefs given to sub-agents are quoted verbatim. Codex and the earliest Claude sessions worked from the task board: a task row (scope, dependencies, linked docs) plus the agent's role file served as the prompt. Those chat prompts were not saved, so they are not reproduced here.

**Developer → Claude: a review against the grading criteria**
> give me the status of the whole project on the basis of [the 10 grading criteria] … [the 5 requirements]

Claude ran the tests and lint itself and rated each criterion with evidence and gaps, instead of repeating what the docs claimed.

**Developer → Claude: scoping a quality pass**
> work on the error handling and logs, testing of the FE, and update the docs correctly also responsible agent use and also work on the maintainability … after working on these things and making all the status strong we will work on the professional readiness, commits and deployment

**Developer → Claude: delegation**
> work on 1 and 2 for now if possible use codex or use your own sub agents

Codex was not available from that session, so Claude ran two sub-agents in parallel on non-overlapping files.

**Claude → sub-agent: JSON logs (excerpt of the brief)**
> Add an opt-in structured (JSON lines) log format so application and AI-workflow logs are machine-readable. … A JSON formatter (stdlib only — no new dependency) emitting one JSON object per line with at least: `ts`, `level`, `logger`, `request_id`, `message` … Do not log full contract text or raw model responses (project rule). … Do NOT edit: anything under `frontend/`, `docs/`, `.ai/`, `README.md` (the parent agent updates docs). Another agent is concurrently editing frontend files.
> **Report back:** files changed with a one-line summary each, the exact JSON field list and event names, test counts, ruff result, and 3 sample JSON log lines from the live check.

**Claude → sub-agent: form validation (excerpt of the brief)**
> Rules derived from the documented shapes / backend … mirror its rules, don't invent stricter ones that contradict it. … Show errors after the user has touched the field or tried to submit — not on first open. … component tests that an invalid edit … shows the message and does NOT call `api.review`.

The pattern in every brief: the goal tied to a requirement, the files to read first, exact rules, paths the agent must not touch, the checks that must pass, and a defined report format.

## Mistakes caught and suggestions rejected

| # | What happened | Whose | How it was caught | Resolution |
|---|---|---|---|---|
| 1 | The model turned "every two weeks" into a 2-day notice period and "Customer **may** inspect" (a right) into an obligation; 3 invented values in total | Product AI (Qwen3-8B) | First `make eval` run | Deterministic grounding checks added; second run: 0 invented values, 0 rights as obligations |
| 2 | The parser dropped short numbered clauses ("4.1 Client shall provide access.") as headings, silently losing contract text | Claude sub-agent | Later testing on the sample contracts | Heading rule tightened; regression test |
| 3 | Frontend pages showed raw field names, sorted dates wrongly in Summary, and attached the wrong citations on Renewals (about 15 issues) | Codex | Claude's code review, then use in Chrome | Fixed before the demo flow was signed off |
| 4 | Backend parts did not match the documented contracts | Codex | Review R01 against `docs/api/` | Reworked by Claude |
| 5 | Error toasts in the Versions tab showed "ApiError: …" instead of the message | Codex | Claude's quality pass | Shared `errorMessage()` helper used everywhere |
| 6 | The brief told the validation sub-agent to make "responsible party" required | Claude (brief) | The sub-agent checked `ai/schemas/obligation.json`, which allows `null`, and kept it optional | Accepted: the schema wins over the brief |
| 7 | A logging change used a column that does not exist (`original_filename`) | Claude | 5 tests failed | Fixed to `file_name` before moving on |
| 8 | The logging doc claimed "model outputs are not logged", but dropped candidates log their value | Claude | Re-reading the code before finishing the doc | Wording corrected to list exactly what is logged |
| 9 | A bulk find-and-replace of test counts also changed the numbers in an older task log, which records a past run | Claude | Checking the diff | Historical numbers restored |
| 10 | Commits would have been authored with the machine's global git identity, not the developer's GitHub account | Environment | Checked before the first commit | Identity set for this repo only |
| R1 | **Rejected:** `npm audit fix --force`, which upgrades React Router to v7 (breaking) the day before the deadline | Tool suggestion | Advisory reviewed: not exploitable here (links only to server IDs) | Deferred and documented; v7 behaviour flags turned on |
| R2 | **Rejected:** deleting the `# noqa: BLE001` comments that ruff reported as unused | Linter suggestion | The comments showed blind-except checks were intended | The `BLE` rule was enabled instead, so the comments now do their job |
| R3 | **Dropped:** the frontend mock-data mode from the original plan | Original plan | The frontend was built against the running backend | Docs that still described it were corrected |

## How the output was verified

Nothing was accepted on an agent's word alone:

| Check | What it gives |
|---|---|
| `make test` | 130 backend/AI tests and 54 frontend tests, plus the typecheck. Re-run by the main session after every delegated task, not taken from the sub-agent's report |
| `make lint` | ruff, ESLint and Prettier must be clean |
| Cross-review | Every Codex and sub-agent result reviewed against the docs ([reviewer checklist](.ai/agents/reviewer.md)) |
| `make eval` | Real-model accuracy against expected outputs for 5 contracts ([results](docs/testing/ai-evaluation.md)) |
| Live checks | Demo flow in Chrome against the real backend and model; a live server to confirm log output |
| Fresh clone | Before the first push, the repo was cloned to an empty directory and the full test suite run there |
| Secret scan | Commit history scanned for keys, passwords and tokens before publishing |
| Claims vs code | Doc statements (counts, log contents, behaviour) checked against the code; see mistakes 8 and 9 |

## What stayed with the developer
- Scope, priorities and the deadline; what is in the MVP and what is excluded.
- Architecture decisions (ADRs 001–008) and dropping Lovable.
- The GitHub account, repository and license. Commits and pushes happened only on the developer's explicit instruction.
- The final demo.

## Responsible AI inside the product
The rule for the coding agents also applies to the model in the app: **the model proposes, code and a person decide.**
- The model never does date arithmetic, never picks between conflicting clauses and never writes the questions shown to users ([ADR 007](docs/decisions/007-deterministic-conflicts-and-citations.md)).
- Every value needs a verbatim quote found in the document, or it is dropped. Missing information stays empty instead of being guessed.
- A person can approve, edit or reject every value, the original AI value is kept, and conflicts block deadlines until resolved.
- The model runs locally, so contract text is not sent to a third-party AI service. The app states it is not legal advice.

## Data and secrets
- The sample contracts are synthetic; no real or confidential documents were given to any agent.
- No API keys are needed. [`.env.example`](.env.example) lists setting names only; `.env`, the database, uploads and logs are git-ignored.
