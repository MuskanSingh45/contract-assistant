# Frontend Pages

All shapes are in `docs/api/`. Labels in **bold** are the UI states that must exist.

## Dashboard: `/dashboard`
`GET /api/dashboard`
- Stat cards: contracts, contracts needing review, upcoming notice deadlines, open obligations, open clarifications.
- Upcoming deadlines list (date, contract, label, "in N days").
- Recent activity list.
- **Empty**: no contracts yet, with a CTA to upload.

## Contracts: `/contracts`
`GET /api/contracts?search=&lifecycle_status=&needs_review=`
- Table: name, parties, expiration (`current_term_end`), notice deadline, lifecycle badge, pending reviews, analysis status.
- Search box, lifecycle filter, "Needs review" toggle.
- Row → `/contracts/:id`. A button goes to Upload.

## Upload: `/contracts/upload`
1. Drop zone that accepts `.pdf`/`.docx` and shows the 20 MB limit. Also validated client-side, but the server is authoritative.
2. Optional name field.
3. Upload with progress → `POST /api/contracts`.
4. On `201` → `POST /api/contracts/{id}/analyze` → navigate to `/contracts/:id/analyzing`.
- **Errors**: `INVALID_DOCUMENT`, `EMPTY_UPLOAD`, `FILE_TOO_LARGE`, `AI_UNAVAILABLE` (uploaded but analysis could not start → offer "Retry analysis").

Uploading a **new version** uses the same component from the Versions tab
(`POST /api/contracts/{id}/versions`).

## Analysis: `/contracts/:id/analyzing`
Poll `GET /api/contracts/{id}/analysis` every 2 s.
- Stepper: Uploading ✓ → Parsing → Extracting (`progress.current/total`) → Validating → Analyzing → Complete.
- **Completed**: summary counts and a "View results" button → `/contracts/:id`. Do not auto-redirect, so the summary is visible in the demo.
- **Failed**: `error.message` plus a "Retry analysis" button (`POST /analyze`). `NO_EXTRACTABLE_TEXT` shows "This looks like a scanned document. OCR is not supported."

## Contract details: `/contracts/:id`
Header: name, version selector (defaults to latest; older versions show a "Viewing version N (not latest)" banner), lifecycle badge.

| Tab | Data | Shows |
|---|---|---|
| Overview | `GET /api/contracts/{id}` | parties, effective date, expiration/current term end, renewal type & period, notice period, **notice deadline** (with "Based on unreviewed data" if `inputs_reviewed` is false, and the `calculation_note` when not calculated), counts, open clarification banner → `/review` |
| Extracted Information | `GET /api/contracts/{id}/extracted-items` | one row per item: label, display value, confidence badge, review badge, source link → drawer, approve/edit/reject. Fields with no item: "Not found in document". |
| Obligations | `GET /api/obligations?contract_id=` | description, responsible party, frequency text, due date (+ "calculated" hint), status, confidence, review, source |
| Versions | `GET /api/contracts/{id}/versions`, `GET .../versions/{vid}/changes` | version list, upload new version, change list (added/removed/modified, before → after, "potentially stale" tag on old values) |

## Obligations: `/obligations`
`GET /api/obligations?status=&review_status=&responsible_party=&due_before=`
Table: description, responsible party, contract, due date, status (operational, editable via
`PATCH`), confidence, review status, source.

## Renewals: `/renewals`
`GET /api/renewals?within_days=`
Table: contract, expiration, current term end, renewal type/period, notice period, **notice
deadline**, days until, calculation status. Blocked rows say "Conflict: resolve in Review".

## Review: `/review`
1. **Clarifications** section (`GET /api/clarifications?status=open`): question, options side by side with their citations, buttons Select / Enter custom value / Dismiss → `POST /api/clarifications/{id}/resolve`.
2. **Queue** (`GET /api/reviews/queue`): each item shows the value, confidence, citation (section · page), **View source**, and Approve / Edit / Reject → `POST /api/reviews`.
- The edit form is driven by `field_name` (date picker for dates; number + unit + anchor for periods; text for parties).
- Each item has a history link → `GET /api/reviews?entity_type=&entity_id=`.

## Source drawer (shared)
`GET /api/citations/{id}`: file name, version, section, page (hidden for DOCX), segment text
with the quote highlighted, and neighbouring context. If `validation_status = not_found`,
show a warning banner.
