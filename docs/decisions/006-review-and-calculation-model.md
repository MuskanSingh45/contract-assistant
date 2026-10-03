# ADR 006 — Review and Calculation Model

## Status
Accepted (2026-10-03).

## Context
Renewal facts (expiration, renewal type, notice period) appeared both as extracted items
and as renewal columns, with no rule for which was authoritative or how either was
reviewed. The API also had two ways to change an obligation (`PATCH` and review `edit`),
and `POST /api/reviews/{item_id}` did not say what kind of item it targeted.

## Decision
1. **Extracted items are the only reviewable source of renewal facts.** The `renewals` row is calculated from them by `backend/utils/dates.py`, recalculated whenever an input changes, and never reviewed directly.
2. **Reviewable entity types:** `extracted_item`, `obligation`. Endpoint: `POST /api/reviews` with `entity_type` + `entity_id` in the body.
3. **Content changes go only through review `edit`.** `PATCH /api/obligations/{id}` changes only the operational `status`.
4. **Conflicts block calculation.** If a single-valued input has two or more non-rejected candidates, the dependent dates are `null` with `calculation_status = blocked_by_conflict`, and a clarification question is opened. The system never picks one.
5. **Unreviewed data is still used for calculation,** but the renewal reports `inputs_reviewed` so the UI can label it.
6. **The original AI value is immutable** (`original_value_json`). The current value may be edited.

## Consequences
One review flow and one history table cover everything. The Renewals page reflects
reviews immediately.
