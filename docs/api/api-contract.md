# API Contract

This is the index and the shared conventions for the REST API between the frontend and FastAPI.
Each resource has its own file with full request/response examples. If a shape is not
documented here, it does not exist yet: do not invent it in the frontend or the backend.
Add it to the docs first.

FastAPI's generated OpenAPI spec (`/openapi.json`, browsable at http://localhost:8000/docs) must match these
docs. If they disagree, fix whichever one is wrong in the same change.

## Conventions

| Topic | Rule |
|---|---|
| Base URL | `/api` (frontend reads it from `VITE_API_BASE_URL`, default `http://localhost:8000/api`) |
| Format | JSON, `snake_case` keys. File uploads use `multipart/form-data`. |
| IDs | Opaque prefixed strings: `ctr_`, `ver_`, `itm_`, `obl_`, `cit_`, `clq_`, `rev_`, `chg_`. Never parse them. |
| Dates | `YYYY-MM-DD` strings. |
| Timestamps | ISO-8601 UTC, e.g. `2026-10-03T10:00:00Z`. |
| Missing values | `null`. Never an empty string or a placeholder date. |
| Lists | `{"items": [...]}`. No pagination for the MVP. |
| Errors | `{"error": {"code", "message", "details", "request_id"}}`. See [errors.md](errors.md). |
| Workspace | Every request carries `X-Workspace-ID: ws_<random>` (the frontend adds it). On the public deployment each workspace has its own data; resources from another workspace answer `*_NOT_FOUND`. Without the header the default (shared) database is used. Locally the header is ignored. [ADR 009](../decisions/009-workspace-isolation.md) |
| Calculated values | Every date the backend calculates (notice deadline, current term end, calculated due dates, `days_until_*`) comes from the API. The frontend only formats it and never calculates it. |
| Version scope | Contract-level and cross-contract endpoints use the **latest version** of each contract unless a `version_id` is passed. |
| Auth | None (out of scope for the MVP). |

## Endpoints

| Method | Path | Purpose | Doc |
|---|---|---|---|
| GET | `/api/health` | Backend, database and AI model service status | below |
| GET | `/api/dashboard` | Dashboard counts, upcoming deadlines, recent activity | [dashboard.md](dashboard.md) |
| GET | `/api/contracts` | Contract list (search/filter) | [contracts.md](contracts.md) |
| POST | `/api/contracts` | Upload a new contract (creates contract + version 1) | [contracts.md](contracts.md) |
| GET | `/api/contracts/{contract_id}` | Contract details / overview | [contracts.md](contracts.md) |
| GET | `/api/contracts/{contract_id}/extracted-items` | Extracted Information tab | [contracts.md](contracts.md) |
| POST | `/api/contracts/{contract_id}/analyze` | Start analysis of a version | [analysis.md](analysis.md) |
| GET | `/api/contracts/{contract_id}/analysis` | Analysis status/progress (poll) | [analysis.md](analysis.md) |
| GET | `/api/contracts/{contract_id}/versions` | Version list | [versions.md](versions.md) |
| POST | `/api/contracts/{contract_id}/versions` | Upload a new version | [versions.md](versions.md) |
| GET | `/api/contracts/{contract_id}/versions/{version_id}/changes` | Comparison with the previous version | [versions.md](versions.md) |
| GET | `/api/obligations` | Cross-contract obligation list | [obligations.md](obligations.md) |
| GET | `/api/obligations/{obligation_id}` | One obligation | [obligations.md](obligations.md) |
| PATCH | `/api/obligations/{obligation_id}` | Change operational status only (open/completed/not_applicable) | [obligations.md](obligations.md) |
| GET | `/api/renewals` | Cross-contract renewal/notice deadlines | [renewals.md](renewals.md) |
| GET | `/api/reviews/queue` | Items awaiting human review | [reviews.md](reviews.md) |
| POST | `/api/reviews` | Approve / edit / reject an extracted item or obligation | [reviews.md](reviews.md) |
| GET | `/api/reviews` | Review history for an item | [reviews.md](reviews.md) |
| GET | `/api/citations/{citation_id}` | Source text and context for the source drawer | [citations.md](citations.md) |
| GET | `/api/clarifications` | Open/resolved clarification questions | [clarifications.md](clarifications.md) |
| POST | `/api/clarifications/{clarification_id}/resolve` | Resolve a conflict/ambiguity | [clarifications.md](clarifications.md) |

## Shared objects

These objects appear in several responses. Resource docs reference them by name.

### Citation (embedded)

```json
{
  "id": "cit_acme_notice",
  "contract_version_id": "ver_acme_1",
  "page": 2,
  "section": "2.2 Renewal",
  "source_text": "at least ninety (90) days before the expiration of the then-current term",
  "validation_status": "verified"
}
```

- `page` is `null` for DOCX documents (DOCX has no reliable page numbers).
- `validation_status`: `verified` means the quote was found exactly in the parsed document. `approximate` means it was found by fuzzy match. `not_found` means the quote could not be located, so the item is suspect. See [../ai/citation-and-review.md](../ai/citation-and-review.md).
- The full surrounding text is fetched separately via `GET /api/citations/{id}`.

### Enums

| Field | Values |
|---|---|
| `confidence` | `high`, `medium`, `low` |
| `review_status` | `pending`, `approved`, `edited`, `rejected` |
| `analysis_status` | `not_started`, `queued`, `processing`, `completed`, `failed` |
| `analysis_stage` | `parsing`, `extracting`, `validating`, `analyzing`, `complete` |
| obligation `status` | `open`, `completed`, `not_applicable` |
| obligation `frequency` | `one_time`, `monthly`, `quarterly`, `annually`, `other` |
| `lifecycle_status` (contract) | `active`, `expiring_soon`, `expired`, `unknown` |
| renewal `calculation_status` | `calculated`, `incomplete`, `blocked_by_conflict` |
| clarification `kind` | `conflict`, `ambiguity`, `missing` |
| clarification `status` | `open`, `resolved`, `dismissed` |

`confidence` (AI) and `review_status` (human) are independent. Obligation `status`
(operational: is it done?) is a third, separate concept.

## Health

### GET `/api/health`

```json
{
  "status": "ok",
  "database": "ok",
  "llm": {
    "provider": "ollama",
    "primary": "ollama",
    "fallback": "groq",
    "model": "qwen3:8b",
    "reachable": true,
    "model_available": true
  }
}
```

`llm.provider` is the service in use right now: the `primary` (`LLM_PROVIDER`), or the
`fallback` (`LLM_FALLBACK_PROVIDER`, `null` if none) when the primary is unavailable. The
online deployment uses `groq` as primary with no fallback.
`status` is `degraded` when the AI service is unreachable or the model is not available. Uploading and
browsing still work in that state; starting an analysis fails with `AI_UNAVAILABLE`.
