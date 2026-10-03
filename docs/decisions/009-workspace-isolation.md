# ADR 009 — Per-browser Workspaces on the Public Deployment

## Status
Accepted (2026-10-04).

## Context
The online demo has no login (authentication is out of scope), but it is public: without
isolation, every visitor saw every uploaded contract and could change anyone's review
decisions. Uploaded text may also be private to the visitor.

## Decision
- Each browser creates a random workspace ID (`ws_` + 32 hex characters), stores it in
  `localStorage`, and sends it as `X-Workspace-ID` on every request.
- With `WORKSPACES=true` (the Render deployment), the backend keeps **one SQLite file per
  workspace** (`WORKSPACE_DIR/<id>.db`). It is created on first use with the migrations and its
  own copy of the demo data. Every connection is opened on that file, including the
  background analysis, so no query can reach another workspace's rows.
- Malformed IDs are rejected (`INVALID_WORKSPACE`, 400) before any path is built.
- Requests without the header (health checks, the API docs page) use the default database.
- Locally `WORKSPACES=false`: the header is ignored and everything uses `data/app.db`.
- Creating workspaces and starting analyses are rate-limited per caller address (and per
  workspace), to protect the free host and the model's free quota (`RATE_LIMITED`, 429).

## Alternatives considered
- **A `workspace_id` column on every table, filtered in every query.** Rejected: about 30
  queries would need the filter, and one missed filter leaks data. A file per workspace makes
  the boundary structural.
- **Shared demo data, read-only.** Rejected: the main demo (resolving the Globex conflict)
  needs writes.
- **Accounts and login.** Out of scope for the MVP.

## Consequences
- The workspace ID is a bearer secret: anyone who has it can open that workspace. It is never
  shown to other users; Settings shows it to its owner and can start a fresh one.
- Clearing browser storage starts a new workspace (the old data is no longer reachable).
- On the free host, all workspaces are wiped on restart, like the demo data.
- Tests: `tests/backend/api/test_workspaces.py`.
