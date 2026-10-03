# Data Flow

## Upload
`POST /api/contracts` (or `/versions`) → validate type/size/signature → store at
`uploads/{contract_id}/{version_id}/{file_name}` → create contract (if new) + version
(`not_started`).

## Analysis (`POST /analyze` → background task)

| Stage | Steps |
|---|---|
| `parsing` | parse PDF/DOCX → normalize → segment (`S1..Sn`, each with page/section). If there is no text → `NO_EXTRACTABLE_TEXT`. |
| `extracting` | group segments into windows (≤ `EXTRACTION_WINDOW_TOKENS`) → per window: `terms` prompt + `obligations` prompt → JSON (Ollama `format` = JSON Schema) |
| `validating` | JSON Schema validation (one retry on failure, then `INVALID_AI_OUTPUT`) → citation validation (segment exists, quote found) → business validation (enum values, date text cross-check, positive numbers) → merge duplicates across windows |
| `analyzing` | conflict detection → clarification questions → date calculation (renewal + obligation due dates) → version comparison with the previous version → **single transaction** persist → `complete` |

Details: [../ai/pipeline.md](../ai/pipeline.md).

## Review
User opens an item → citation drawer (`GET /citations/{id}`) → approve/edit/reject
(`POST /reviews`) → item status updated + review row appended → if the item is a date
input, renewal and obligation due dates are recalculated in the same transaction.

## Clarification
Open question → user selects an option, enters a custom value, or dismisses → item
statuses updated, review rows linked to the clarification → recalculation.

## New version
New upload → version N+1 → independent analysis → comparison with N (`version_changes`) →
the Versions tab shows changed items and marks potentially stale ones → the new version's
items start as `pending`. Previous reviews stay on version N; they are not copied forward.
