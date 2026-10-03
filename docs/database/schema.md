# Database Schema

**Source of truth: [`db/migrations/001_initial.sql`](../../db/migrations/001_initial.sql).**
This page explains it. If they disagree, the migration wins and this page must be fixed.

SQLite, accessed with the Python standard library `sqlite3` (no ORM). See
[decisions.md](decisions.md).

## Tables

| Table | Purpose | Written by |
|---|---|---|
| `contracts` | Logical agreement (id, name). No derived display fields. | upload |
| `contract_versions` | One uploaded file, plus its analysis status/stage/error, model and prompt version | upload, analysis |
| `document_segments` | Parsed, normalized text split into citable segments (page, section, text) | analysis: parsing |
| `extracted_items` | AI-extracted facts: party, effective_date, expiration_date, initial_term, renewal_terms, notice_period, termination_clause | analysis, review (edit), clarification (custom) |
| `obligations` | AI-extracted obligations with rule and due date | analysis, review, PATCH status |
| `renewals` | **Calculated** renewal/notice result per version (one row per version) | backend date calculation |
| `citations` | Evidence quote + location for an item, obligation or clarification | analysis |
| `clarification_questions` | Conflicts / ambiguities / missing info requiring a human | analysis, resolve |
| `clarification_options` | Which items a clarification is choosing between | analysis |
| `reviews` | Append-only history of human review actions | review, resolve |
| `version_changes` | Diff between a version and the previous version | analysis: analyzing |
| `schema_migrations` | Applied migrations | migration runner |

## Key design points

### Values are JSON, and the original is kept

`extracted_items.value_json` holds the current value (possibly human-edited).
`original_value_json` holds the AI output and is never updated. The per-field value
shapes are in [../api/contracts.md](../api/contracts.md). `obligations` stores content in
columns and the AI original in `original_value_json`.

### Three status concepts

| Column | Meaning | Values |
|---|---|---|
| `confidence` | AI's confidence | high / medium / low |
| `review_status` | Human review state (current) | pending / approved / edited / rejected |
| `obligations.status` | Operational state of the obligation | open / completed / not_applicable |

`reviews` holds the history. The current `review_status` is stored on the item for simple
querying.

### Renewals are calculated, not extracted

The renewal facts are extracted as `extracted_items` (one reviewable source of truth). The
`renewals` row is the output of `backend/utils/dates.py` and is recalculated whenever an
input item changes. See [../architecture/date-calculation.md](../architecture/date-calculation.md).

### Citations

- They are polymorphic: `entity_type` + `entity_id` point to an extracted item, obligation or clarification. One entity can have many citations (a conflict has at least two). There is no FK on `entity_id`; the service layer enforces it.
- `segment_id` → `document_segments`. `page` and `section` are copied from the segment and are **never** taken from the model.
- `validation_status`: verified / approximate / not_found. See [../ai/citation-and-review.md](../ai/citation-and-review.md).
- Naming: the version column is `contract_version_id` everywhere. The earlier name `document_version_id` is retired.

### Versions

- `UNIQUE(contract_id, version_number)`. A new upload is always a new row.
- Re-analysis of the same version replaces that version's analysis output (items, obligations, citations, clarifications, renewal, changes) but **not** `reviews`.
- "Potentially stale" is not a column. It is derived from `version_changes` (see [../api/versions.md](../api/versions.md)).

### Conventions

- IDs: prefixed TEXT (`ctr_`, `ver_`, `seg_`, `itm_`, `obl_`, `ren_`, `cit_`, `clq_`, `rev_`, `chg_`) + uuid4 hex.
- Dates `YYYY-MM-DD`. Timestamps ISO-8601 UTC. Booleans `0/1`.
- `PRAGMA foreign_keys = ON` on every connection (SQLite defaults to off).
- Deleting a contract cascades to everything, but there is no delete endpoint in the MVP.

## Demo data

`db/seeds/development.sql` contains:

- **Acme Services Agreement**: clean, with notice deadline 2026-11-02.
- **Globex Hosting Agreement**: 90-day vs 60-day notice conflict, an open clarification, and the renewal `blocked_by_conflict`.

It matches the examples in `docs/api/`.
