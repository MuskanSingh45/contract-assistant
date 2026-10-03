# AI Extraction

Machine-readable schemas: `ai/schemas/extraction.json` (terms) and
`ai/schemas/obligation.json`. This page explains them.

## Common shape: every candidate

```json
{
  "value": { ... },
  "confidence": "high | medium | low",
  "evidence": [ { "segment_id": "S3", "quote": "verbatim text copied from segment S3" } ],
  "ambiguity_note": "string or null"
}
```

- `evidence` is required and holds 1–3 entries. `quote` must be copied **verbatim** from the named segment and be 300 characters or less.
- `ambiguity_note` is set when the text is unclear, conditional, or seems to contradict another clause. Otherwise it is `null`.

## Missing information

Every field is an **array of candidates**. **Not found = empty array `[]`.** The model must
not guess, default, or infer from typical contracts. An empty array is a correct answer.

If the window contains two different statements for the same field (e.g. 90 days and 60
days), the model returns **both** as separate candidates and does not choose.

## Terms output (`extraction.json`)

```json
{
  "parties": [
    { "value": { "name": "Acme Corporation", "role": "customer" },
      "confidence": "high",
      "evidence": [ { "segment_id": "S1", "quote": "Acme Corporation (\"Customer\")" } ],
      "ambiguity_note": null }
  ],
  "effective_date": [
    { "value": { "date_text": "January 31, 2025", "date": "2025-01-31" },
      "confidence": "high",
      "evidence": [ { "segment_id": "S1", "quote": "as of January 31, 2025 (the \"Effective Date\")" } ],
      "ambiguity_note": null }
  ],
  "expiration_date": [
    { "value": { "date_text": "January 31, 2027", "date": "2027-01-31" }, "...": "..." }
  ],
  "initial_term": [],
  "renewal_terms": [
    { "value": { "type": "automatic", "period_value": 12, "period_unit": "months" }, "...": "..." }
  ],
  "notice_period": [
    { "value": { "value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal" }, "...": "..." }
  ],
  "termination_clause": []
}
```

| Field | `value` | Notes |
|---|---|---|
| `parties` | `name`, `role` (as named in the contract, or null) | One candidate per party |
| `effective_date`, `expiration_date` | `date_text` (verbatim), `date` (`YYYY-MM-DD` or null if the text is not a calendar date) | `date` only normalizes `date_text`. The backend cross-checks it. Relative dates ("two years after the Effective Date") are **not** expiration dates; they go in `initial_term`. |
| `initial_term` | `value`, `unit` (days/months/years) | Term length, e.g. "initial term of two (2) years" |
| `renewal_terms` | `type` (automatic/optional/none), `period_value`, `period_unit` | `none` only if the contract explicitly says there is no renewal; otherwise `[]` |
| `notice_period` | `value`, `unit` (days/business_days/months), `anchor` (expiration_date/renewal_date/other), `purpose` (non_renewal/termination/other) | |
| `termination_clause` | `summary` (one sentence) | Informational; no calculation |

Stored as `extracted_items` with `field_name` = the singular key (`parties` → `party`).

## Obligations output (`obligation.json`)

```json
{
  "obligations": [
    {
      "value": {
        "description": "Submit quarterly compliance report",
        "responsible_party": "Example Services Ltd.",
        "frequency": "quarterly",
        "frequency_text": "within thirty (30) days after the end of each calendar quarter",
        "due_rule": { "basis": "calendar_period_end", "offset_days": 30 },
        "due_date_text": null
      },
      "confidence": "high",
      "evidence": [ { "segment_id": "S4", "quote": "Service Provider shall submit a compliance report to Customer within thirty (30) days after the end of each calendar quarter." } ],
      "ambiguity_note": null
    }
  ]
}
```

- `description`: an imperative and short summary (12 words or fewer). It is not legal advice.
- `responsible_party`: the party name as defined in the contract, "Either party", or null if not stated.
- `frequency`: one_time / monthly / quarterly / annually / other, or null.
- `due_rule.basis`: explicit_date / effective_date_anniversary / calendar_period_end / renewal_notice_deadline / unspecified. The meanings are in [../architecture/date-calculation.md](../architecture/date-calculation.md) §6.
- `due_date_text`: the verbatim date when `basis = explicit_date`, else null.
- Only obligations a party **must** perform. Rights ("may terminate") are not obligations. The exception is a notice that must be given to exercise or avoid renewal; it is included with an `ambiguity_note` saying that it is conditional.

## What the model must not do

- Calculate dates (no "deadline = 2026-11-02").
- Output page numbers or section names (these come from segments).
- Fill fields from general knowledge or "typical" terms.
- Choose between contradictory clauses.
