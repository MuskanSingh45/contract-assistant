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

No other AI tools were used. The product itself uses Qwen models (Qwen3-8B via Ollama locally, Qwen via Groq in the online demo); those are part of the application, not coding tools.

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
| Groq provider, Render/Vercel deployment, live verification (Q09) | Claude (developer created the accounts and entered the API key) | Claude: 13 new tests, evaluation on Groq, live end-to-end analysis | Accepted |
| Frontend TypeScript → JavaScript conversion (Q08) | Claude (mechanical type removal with Sucrase; types kept as JSDoc) | Claude: all 54 frontend tests, ESLint, build | Accepted |
| Product scope, deadline, architecture decisions, stack choice, dropping Lovable, license, GitHub account | **Not delegated:** the developer | — | — |

## Representative prompts

Two kinds of prompt drove the work:

- **Developer → Claude:** short chat instructions. They are shown below **edited for clarity and precision from the original chat messages**; each keeps the original intent, scope and constraints, and the outcome note says what happened.
- **Claude → sub-agent:** written briefs. These are **quoted verbatim** (excerpts).

Codex and the earliest Claude sessions worked from the task board: a task row (scope, dependencies, linked docs) plus the agent's role file served as the prompt. Those chat sessions were not saved, so they are not reproduced.

### Developer → Claude (edited for clarity)

**1. Audit against the grading rubric**
> Assess the repository against the 10 grading criteria and the 5 hard requirements. For each, give a status (strong / partial / missing) backed by evidence you verify yourself: run the test suites and linters, inspect the code and git state, and do not rely on what the docs claim. List the gaps in priority order with an effort estimate.

*Outcome:* the audit found no git history, an empty LICENSE, no frontend tests, 40 lint findings and stale docs; these became tasks Q01–Q04.

**2. Quality pass, scoped to specific criteria**
> Bring error handling and logging, frontend testing, documentation accuracy, responsible-agent-use evidence and maintainability to "strong". Keep the scope to those criteria: do not commit, and leave packaging and deployment for a later step. Every claim in the docs must match the code.

*Outcome:* request-ID correlation, rotating logs, a frontend error boundary, 42 Vitest tests, a ruff/ESLint/Prettier baseline and reconciled docs (Q01–Q04).

**3. Parallel delegation with isolation**
> Close the two remaining gaps: (1) machine-readable JSON logs covering the AI workflow, and (2) client-side validation in the review forms. Delegate them to separate sub-agents running in parallel on non-overlapping paths, then review both diffs and re-run every check yourself before accepting them.

*Outcome:* Codex was not reachable from that session, so two Claude sub-agents were used; both results were reviewed and re-verified (Q05–Q06).

**4. Publish under the developer's identity**
> Create a public GitHub repository under the MuskanSingh45 account and push a logical commit history (scaffolding → docs → db → backend → AI → frontend → tests). Author every commit as MuskanSingh45 using the GitHub no-reply address, scoped to this repo only, without changing the machine's global git identity. Verify the identity and run a secret scan before pushing.

*Outcome:* nine commits, pushed only after the full suite passed in a fresh clone.

**5. Stack change with a plan first**
> Evaluate converting the frontend from TypeScript to JavaScript. Present the options, the plan, the risks and a time estimate before changing anything. Then carry out the chosen option without changing behaviour, and keep the API data shapes documented.

*Outcome:* Option 1 (frontend only): Sucrase type-stripping, JSDoc typedefs, all tests green, and a styling regression caught in the browser (mistake 11).

**6. Remove dead code, verify before deleting**
> Find placeholder modules and empty directories that nothing imports or references. Remove them, and update every doc that still describes them.

*Outcome:* `backend/models/`, four unused schema modules and redundant `.gitkeep` files removed; three docs corrected.

**7. Free deployment under hard constraints**
> Deploy the application on free tiers only, with no paid model API. The model must keep working when the developer's laptop is off. Research the current free-tier limits before choosing; do not rely on remembered pricing.

*Outcome:* Hugging Face Docker Spaces turned out to need a paid plan (mistake 12). Final setup: Vercel (frontend), Render (backend) and Groq's free API (model), with a provider switch so local runs still use Ollama. Re-evaluated and verified end to end on the live services.

**8. Keep every document consistent with the shipped system**
> Update all documentation to match the current state: stack, deployment, model providers, test counts and limitations. Check the GitHub repository metadata as well.

### Claude → sub-agent (verbatim excerpts)

**JSON logs**
> Add an opt-in structured (JSON lines) log format so application and AI-workflow logs are machine-readable. … A JSON formatter (stdlib only — no new dependency) emitting one JSON object per line with at least: `ts`, `level`, `logger`, `request_id`, `message` … Do not log full contract text or raw model responses (project rule). … Do NOT edit: anything under `frontend/`, `docs/`, `.ai/`, `README.md` (the parent agent updates docs). Another agent is concurrently editing frontend files.
> **Report back:** files changed with a one-line summary each, the exact JSON field list and event names, test counts, ruff result, and 3 sample JSON log lines from the live check.

**Form validation**
> Rules derived from the documented shapes / backend … mirror its rules, don't invent stricter ones that contradict it. … Show errors after the user has touched the field or tried to submit — not on first open. … component tests that an invalid edit … shows the message and does NOT call `api.review`.

### What made the prompts work
- **Goal tied to a requirement or criterion**, so the agent can judge "done".
- **Explicit scope and non-goals** ("do not commit", "frontend only", owned paths).
- **Verification built in:** run the tests, check identity, scan for secrets, re-run the sub-agent's checks.
- **Plan before irreversible or large changes** (stack change, deployment, history rewrite).
- **A defined report format** for sub-agents, so their results can be checked against the diff.

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
| 11 | After the TypeScript → JavaScript conversion, all tests, lint and the build passed, but the app rendered with **no styling**: the Tailwind config still only scanned `.ts`/`.tsx` files for class names | Claude | Opening the app in Chrome after the automated checks | Tailwind globs changed to `.js`/`.jsx`; the app was rechecked page by page with no console errors. Shows why the manual browser check stays in the process |
| 12 | Claude planned the free deployment on Hugging Face's free CPU Spaces, believing they accepted Docker. They now need a PRO subscription for Docker Spaces | Claude (outdated knowledge) | The Space creation was refused with HTTP 402 | Nothing was created; the untested Dockerfile was removed. Free tiers were then checked on the web before choosing again |
| 13 | The research found Groq serving Qwen3-32B, but the live model list showed `qwen/qwen3.8-27b` instead | Web sources (out of date) | Calling Groq's `/models` with the account's key before writing any code | Built against the model that actually exists, then re-ran the evaluation on it |
| R1 | **Rejected:** `npm audit fix --force`, which upgrades React Router to v7 (breaking) the day before the deadline | Tool suggestion | Advisory reviewed: not exploitable here (links only to server IDs) | Deferred and documented; v7 behaviour flags turned on |
| R2 | **Rejected:** deleting the `# noqa: BLE001` comments that ruff reported as unused | Linter suggestion | The comments showed blind-except checks were intended | The `BLE` rule was enabled instead, so the comments now do their job |
| R3 | **Dropped:** the frontend mock-data mode from the original plan | Original plan | The frontend was built against the running backend | Docs that still described it were corrected |

## How the output was verified

Nothing was accepted on an agent's word alone:

| Check | What it gives |
|---|---|
| `make test` | 144 backend/AI tests and 54 frontend tests, plus static checks (the TypeScript typecheck while the frontend was TypeScript, ESLint after the move to JavaScript). Re-run by the main session after every delegated task, not taken from the sub-agent's report |
| `make lint` | ruff, ESLint and Prettier must be clean |
| Cross-review | Every Codex and sub-agent result reviewed against the docs ([reviewer checklist](.ai/agents/reviewer.md)) |
| `make eval` | Real-model accuracy against expected outputs for 5 contracts ([results](docs/testing/ai-evaluation.md)) |
| Live checks | Demo flow in Chrome against the real backend and model; a live server to confirm log output |
| Fresh clone | Before the first push, the repo was cloned to an empty directory and the full test suite run there |
| Secret scan | Commit history scanned for keys, passwords and tokens before publishing |
| Claims vs code | Doc statements (counts, log contents, behaviour) checked against the code; see mistakes 8 and 9 |

## What stayed with the developer
- Scope, priorities and the deadline; what is in the MVP and what is excluded.
- Architecture decisions (ADRs 001–008), dropping Lovable, and moving the frontend from TypeScript to JavaScript.
- The GitHub account, repository and license. Commits and pushes happened only on the developer's explicit instruction.
- The final demo.

## Responsible AI inside the product
The rule for the coding agents also applies to the model in the app: **the model proposes, code and a person decide.**
- The model never does date arithmetic, never picks between conflicting clauses and never writes the questions shown to users ([ADR 007](docs/decisions/007-deterministic-conflicts-and-citations.md)).
- Every value needs a verbatim quote found in the document, or it is dropped. Missing information stays empty instead of being guessed.
- A person can approve, edit or reject every value, the original AI value is kept, and conflicts block deadlines until resolved.
- Run locally, the model runs on the user's machine and contract text stays there. The online demo uses Groq's hosted API because no free host can run the model; the Help page and README say so, and only synthetic sample contracts are meant to be uploaded there. The Groq key lives only in `.env` and the Render dashboard. The app states it is not legal advice.

## Data and secrets
- The sample contracts are synthetic; no real or confidential documents were given to any agent.
- No API keys are needed. [`.env.example`](.env.example) lists setting names only; `.env`, the database, uploads and logs are git-ignored.
