# .ai: Shared Context for Coding Agents

Several agents work on this repo (Claude and Codex; Lovable was planned and dropped). This
directory makes sure they all work from the same plan. How this worked in practice, and how
agent output was verified: [AGENT_USAGE.md](../AGENT_USAGE.md).

**Every agent, before changing anything:**

1. Read [project-context.md](project-context.md): what we're building, current status, and the rules that must not be broken.
2. Read [coding-rules.md](coding-rules.md).
3. Read your role file in [agents/](agents/).
4. Read [tasks/current.md](tasks/current.md) and pick up only the task assigned to you.
5. Read the `docs/` files your task links to.

When you finish, follow [workflow.md](workflow.md).

| File | Purpose |
|---|---|
| project-context.md | Product, stack, status, non-negotiable rules, what NOT to build |
| coding-rules.md | Conventions for all code |
| workflow.md | How tasks move, how to hand off, when to update docs |
| agents/*.md | Per-agent scope, owned paths, required reading |
| tasks/current.md | The active task board |
| tasks/completed/ | One file per finished task (what changed, what's left) |
