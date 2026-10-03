# Citations and Human Review

## Citations

Every extracted item and obligation needs evidence. A citation links it to an exact place
in the parsed document:

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

### How a citation is produced

1. The model returns `evidence: [{segment_id: "S3", quote: "..."}]`.
2. `ai/validators/citation_validator.py` checks the evidence:

| Check | Result |
|---|---|
| `segment_id` is not a segment in the window the model saw | discard this evidence entry |
| normalized `quote` is an exact substring of the normalized segment text | `verified`, with `char_start`/`char_end` recorded |
| else `rapidfuzz.fuzz.partial_ratio(quote, segment) ≥ 90` | `approximate`, with best-match offsets recorded |
| else | `not_found` |

3. `page` and `section` are copied from the stored segment. **The model never supplies them.**

"Normalized" here means lowercase, whitespace collapsed, and curly quotes/dashes converted
to straight ones. The same function (`ai/text.py`, `normalize_for_match`) is used for the segment text.

### Effects on the item

- **No evidence entries remain** (none given, or all discarded): the candidate is **dropped** as unsupported and counted in the analysis log. This is the main guard against made-up data.
- Only `not_found` citations: the item is kept, confidence is forced to `low`, and the UI shows a warning. PDF text extraction sometimes mangles text, so a human decides.
- At least one `verified` citation: no change.

### UI
The item shows "Source: Section 2.2 · Page 2" and a **View source** button that opens the
source drawer (`GET /api/citations/{id}`) with the segment text and the quote highlighted.
DOCX citations show the section only.

## Human review

Confidence and review status are independent. See [confidence.md](confidence.md).

| Action | Effect |
|---|---|
| Approve | `review_status = approved` |
| Edit | the current `value` is replaced and `review_status = edited`. `original_value` is kept unchanged. |
| Reject | `review_status = rejected`. The item is excluded from calculations but kept. |

- Every action appends a row to `reviews` (the history).
- Reviewing a date input recalculates the renewal and due dates immediately.
- Conflicts are resolved through clarifications ([clarification.md](clarification.md)), which create review rows too.

API: [../api/reviews.md](../api/reviews.md).
