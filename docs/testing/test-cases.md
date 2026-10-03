# Test Cases

Reference "today" for date tests: **2026-10-03**.

## Upload (`tests/backend/api/`)
1. Valid PDF → contract + version 1 created, `analysis_status = not_started`.
2. Valid DOCX → same.
3. `.txt` or a PDF renamed from `.exe` → `INVALID_DOCUMENT` (signature check).
4. Empty upload / 0-byte file → `EMPTY_UPLOAD`.
5. > 20 MB → `FILE_TOO_LARGE`.
6. New version with an identical hash → `DUPLICATE_VERSION`.

## Parsing (`tests/backend/documents/`)
1. PDF segments carry page numbers; DOCX segments have `page = None`.
2. Numbered headings become `section`.
3. A word hyphenated across a line break is rejoined; curly quotes are normalized.
4. An image-only PDF → `NO_EXTRACTABLE_TEXT`.

## Date calculation (`tests/backend/services/test_dates.py`, pure unit tests)
1. Acme: expiration 2027-01-31, 90 days → notice deadline **2026-11-02**.
2. Months clamp: 2027-03-31 − 1 month → 2027-02-28.
3. Business days: 10 business days before Monday 2026-11-16 → 2026-11-02.
4. Roll-forward: expiration 2026-01-31, automatic 12 months, today 2026-10-03 → current term end 2027-01-31.
5. Not automatic and expired → lifecycle `expired`.
6. No expiration, effective 2025-01-31 + initial term 2 years → expiration 2027-01-31 (`calculated`).
7. Explicit expiration ≠ effective + term → conflict.
8. Two non-rejected renewal-relevant notice periods (90 / 60 days) → `blocked_by_conflict`, deadline `null`.
9. A 30-day termination notice with `anchor: other` alongside a 90-day non-renewal notice → no conflict; deadline uses 90 days.
10. Rejecting the 60-day item → calculation succeeds with 90 days.
11. Quarterly `calendar_period_end` + 30 → 2026-10-30. Annual anniversary from 2025-01-31 → 2027-01-31.
12. `anchor = other` → `incomplete`.

## Citation validation (`tests/ai/citations/`)
1. Exact quote → `verified` with correct offsets.
2. Quote differing only in whitespace/curly quotes → `verified`.
3. Quote with one OCR-like typo → `approximate`.
4. Invented quote → `not_found`, confidence forced to `low`.
5. Unknown segment label → evidence discarded; a candidate with no remaining evidence → dropped.

## Conflicts (`tests/ai/conflicts/`)
1. Two different expiration dates → one conflict clarification with two options.
2. The same value found in two windows → merged into one item with two citations, no conflict.
3. Two parties → no conflict (multi-valued).

## Extraction (`tests/ai/extraction/`, needs Ollama; marked `@pytest.mark.llm`)
1. Acme sample matches `contracts/fixtures/expected-extractions/acme-services-agreement.json`.
2. Missing values → `[]`, never invented.
3. "Either party may terminate" is not an obligation.
4. Invalid JSON on the first attempt → retry; second failure → `INVALID_AI_OUTPUT`, nothing persisted.

## Review (`tests/backend/api/`)
1. Approve → `approved`, one history row.
2. Edit → new `value`, `original_value` unchanged, `edited`, history has previous/new.
3. Reject a date input → renewal recalculated in the response.
4. Approve with `value` → `INVALID_REVIEW_ACTION`. Edit with an invalid date → `VALIDATION_ERROR`.
5. `PATCH /obligations/{id}` with `description` → `VALIDATION_ERROR`.

## Clarifications
1. Select 90-day option → 90 approved, 60 rejected, renewal calculated (Globex: 2026-10-02, already passed, so `days_until_notice_deadline = -1`). Selecting 60 days instead gives 2026-11-01.
2. Custom value → new item with `origin = human`; options rejected.
3. Resolve twice → `CLARIFICATION_ALREADY_CLOSED`.

## Versioning
1. New upload → version 2. Version 1 rows unchanged.
2. Notice period changed between versions → one `modified` change; version 1's item is potentially stale.
3. Re-analysis of a version replaces its items but keeps `reviews` rows.

## Analysis failure
1. Ollama down → `POST /analyze` returns `AI_UNAVAILABLE` (503).
2. Failure mid-analysis → status `failed`, no partial items persisted.
3. Server restart during analysis → version marked `failed` on startup.
