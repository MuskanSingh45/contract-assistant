# Contract Obligation and Renewal Assistant: Documentation

This directory is the shared documentation and the source of truth for the Contract
Obligation and Renewal Assistant. Agents start at [`../.ai/README.md`](../.ai/README.md).

The application helps users upload contracts, extract contractual information, identify
obligations and renewal terms, calculate deadlines deterministically, and review
AI-generated information with source citations. It is **not legal advice**.

## Core principle

> AI extracts and interprets. Deterministic application code validates, calculates dates,
> detects conflicts, persists state and controls the workflow.

## Map

| Area | Start here | Notes |
|---|---|---|
| Product | [product/requirements.md](product/requirements.md) | scope, user flows, stories, terminology |
| Architecture | [architecture/overview.md](architecture/overview.md) | backend layout, data flow, **[date calculation](architecture/date-calculation.md)**, [errors and logging](architecture/backend-architecture.md#errors), deployment |
| API | [api/api-contract.md](api/api-contract.md) | conventions, endpoint index, one file per resource |
| Database | [database/schema.md](database/schema.md) | source of truth is `db/migrations/` |
| AI | [ai/overview.md](ai/overview.md) | pipeline, extraction, citations, confidence, conflicts, model config |
| Frontend | [frontend/architecture.md](frontend/architecture.md) | routes, pages with data sources, components |
| Decisions | [decisions/](decisions/) | ADR 001–008 |
| Testing | [testing/strategy.md](testing/strategy.md) | what each suite covers, test cases with concrete dates, AI evaluation |
| Process | [../AGENT_USAGE.md](../AGENT_USAGE.md) | how AI coding agents were used and checked |

## Sources of truth (when two things disagree)

| Topic | Wins |
|---|---|
| DB schema | `db/migrations/*.sql` |
| API shapes | `docs/api/*.md` (FastAPI OpenAPI must match) |
| LLM output shape | `ai/schemas/*.json` |
| Date rules | `docs/architecture/date-calculation.md` |
| Demo data | `db/seeds/development.sql` = examples in `docs/api/` |
| Current work | `.ai/tasks/current.md` |
