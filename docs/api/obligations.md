# Obligations API

## Obligation object

```json
{
  "id": "obl_acme_report",
  "contract_id": "ctr_acme",
  "contract_name": "Acme Services Agreement",
  "contract_version_id": "ver_acme_1",
  "description": "Submit quarterly compliance report",
  "responsible_party": "Example Services Ltd.",
  "frequency": "quarterly",
  "frequency_text": "within thirty (30) days after the end of each calendar quarter",
  "due_rule": { "basis": "calendar_period_end", "offset_days": 30 },
  "due_date": "2026-10-30",
  "due_date_source": "calculated",
  "days_until_due": 27,
  "status": "open",
  "confidence": "high",
  "review_status": "pending",
  "original_value": {
    "description": "Submit quarterly compliance report",
    "responsible_party": "Example Services Ltd.",
    "frequency": "quarterly"
  },
  "ambiguity_note": null,
  "in_open_clarification": false,
  "citations": [ /* Citation objects */ ],
  "updated_at": "2026-09-28T09:02:40Z"
}
```

Three separate concepts. Do not merge them in the UI:

- `confidence`: how sure the AI was.
- `review_status`: whether a human approved, edited or rejected the extraction.
- `status`: operational state of the obligation itself (`open`, `completed`, `not_applicable`).

The rule and the date are separate. `frequency`/`frequency_text`/`due_rule` describe the
rule as written. `due_date` is either taken from the contract (`due_date_source:
"explicit"`) or calculated by the backend (`"calculated"`). It is `null` when the rule
cannot be calculated (`due_rule.basis = "unspecified"`), and the UI then shows
`frequency_text`. Calculation rules: [../architecture/date-calculation.md](../architecture/date-calculation.md).

## GET `/api/obligations`

Cross-contract list. Latest version of each contract only, unless `version_id` is given.
Rejected obligations are excluded unless `review_status=rejected` is requested.

| Param | Meaning |
|---|---|
| `contract_id` | Filter to one contract (used by the contract details Obligations tab) |
| `version_id` | Specific version (requires `contract_id`) |
| `status` | `open` / `completed` / `not_applicable` |
| `review_status` | `pending` / `approved` / `edited` / `rejected` |
| `responsible_party` | Case-insensitive contains |
| `due_before` | `YYYY-MM-DD`, obligations with `due_date` on or before this date |

Response `200`: `{"items": [Obligation, ...]}`, sorted by `due_date` ascending, nulls last.

## GET `/api/obligations/{obligation_id}`

Response `200`: Obligation object. Error: `OBLIGATION_NOT_FOUND`.

## PATCH `/api/obligations/{obligation_id}`

Changes the **operational status only**. Content corrections (description, party,
frequency, due date) go through `POST /api/reviews` with `action: "edit"`, so that every
content change is in the review history.

Request:

```json
{ "status": "completed" }
```

Response `200`: updated Obligation object.
Errors: `OBLIGATION_NOT_FOUND`, `VALIDATION_ERROR` (any field other than `status`).
