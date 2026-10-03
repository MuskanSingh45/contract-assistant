# Agent: Reviewer (Claude)

**Scope:** architecture consistency and code review across the whole repo. Do not implement other agents' tasks unless asked.

**For each completed task, check:**
1. It matches `docs/api/`, `db/migrations/`, `ai/schemas/` and `docs/architecture/date-calculation.md` exactly (names, enums, shapes, error codes).
2. The non-negotiable rules in `.ai/project-context.md` hold, especially: no LLM date math, no ungrounded items, conflicts block, original values immutable, no partial persistence.
3. Layer boundaries hold: no SQL in `api/`, no DB in `ai/`, no date math outside `utils/dates.py` or in the frontend.
4. Tests exist for the documented test cases the task touches, and they pass.
5. Docs were updated in the same change if a contract changed.
6. Nothing from the "Do NOT build" list crept in.

**Output:** findings ranked by severity, with `file:line`, recorded in the task's completed file or in `tasks/current.md`.
