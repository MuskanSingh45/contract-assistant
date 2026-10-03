# Acceptance Criteria

## Upload
- User can upload supported contract.
- Upload creates contract and version.
- Unsupported files are rejected clearly.

## Analysis
- Analysis has visible state.
- Analysis produces structured information.
- Invalid AI output does not silently persist.

## Extraction
- Key fields display correctly.
- Confidence is visible.
- Missing information is not invented.

## Citations
- Every extracted item and obligation has at least one citation, or is dropped.
- User can open the source drawer and see the highlighted quote.
- Page and section come from the parsed document, never from the model.
- Unverifiable quotes are flagged, not hidden.

## Obligations
- Obligations are visible.
- Responsible party shown where available.
- Status and confidence shown.

## Renewals
- Expiration shown.
- Renewal rule shown.
- Notice period shown.
- Notice deadline calculated deterministically (Acme → 2026-11-02).
- Conflicting notice periods block the deadline and create a clarification question.

## Clarifications
- Open questions are visible in Review with both sources.
- Resolving one recalculates the deadline immediately.

## Review
- Approve/edit/reject work and are recorded in history.
- The original AI value is preserved after an edit.
- Review status is separate from AI confidence.

## Versions
- Multiple versions retained.
- Version metadata visible.
- Changes can be reviewed.
