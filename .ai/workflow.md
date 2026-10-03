# Workflow

## Task lifecycle
1. **Pick**: take a task from `tasks/current.md` that is assigned to your agent and whose dependencies are done. Set it to `in progress`.
2. **Read**: the docs listed in the task, plus your agent file.
3. **Build**: stay inside your owned paths (see `agents/`). If you need a change outside them, or to a documented contract, stop and write it under **Blocked / questions** in `tasks/current.md`.
4. **Verify**: run the relevant tests (`pytest tests/...`). For AI changes, run `scripts/evaluate_ai.py`.
5. **Record**: add `tasks/completed/YYYY-MM-DD-<task-id>.md` covering what changed, the files touched, how it was verified, and any follow-ups. Mark the task `done` in `current.md`.
6. **Review**: Claude reviews completed backend/AI tasks against the docs (see `agents/reviewer.md`).

## Changing a contract (API shape, schema, enum, rule)
1. Propose it in `tasks/current.md` under Blocked / questions.
2. Once agreed, update the docs first, then the migration/schema, then the code, all in the same change.
3. Note it in the completed-task file so the other agents see it.

## Git
- Branch per task: `task/<id>-<short-name>`. Small commits. No commits of `.env`, `data/`, `uploads/`.
- The repo was initialized on 2026-10-03 with no remote yet.
