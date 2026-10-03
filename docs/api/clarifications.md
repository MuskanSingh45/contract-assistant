# Clarifications API

A clarification question is created during analysis when the system cannot safely decide.
See [../ai/clarification.md](../ai/clarification.md) for when that happens.

| kind | Created when | Options |
|---|---|---|
| `conflict` | Two or more non-rejected items with different values for a single-valued field (e.g. notice period 90 vs 60 days) | the conflicting items |
| `ambiguity` | The model reported an `ambiguity_note` on an item that is an input to a date calculation | the item |
| `missing` | `expiration_date` and `initial_term` were both not found, so no deadline can be calculated | none |

## Clarification object

```json
{
  "id": "clq_globex_notice",
  "contract_id": "ctr_globex",
  "contract_name": "Globex Hosting Agreement",
  "contract_version_id": "ver_globex_1",
  "kind": "conflict",
  "field_name": "notice_period",
  "question": "Two sections specify different notice periods (90 days in 3.2 Renewal, 60 days in 12.1 Notices). Which provision should be treated as the applicable notice rule?",
  "status": "open",
  "options": [
    { "entity_type": "extracted_item", "entity_id": "itm_globex_notice_90",
      "display_value": "90 days before expiration (non-renewal)", "review_status": "pending", "citations": [ /* Citation */ ] },
    { "entity_type": "extracted_item", "entity_id": "itm_globex_notice_60",
      "display_value": "60 days before expiration (non-renewal)", "citations": [ /* Citation */ ] }
  ],
  "citations": [ /* evidence for the question itself (all options' quotes) */ ],
  "resolution": null,
  "resolution_note": null,
  "created_at": "2026-10-01T11:04:00Z",
  "resolved_at": null
}
```

Question text is generated from a **template** in `ai/pipeline/clarification.py` (deterministic code), not by the LLM. Live example from the Globex sample:
"Two sections specify different notice periods (90 days before expiration (non-renewal) in 3.2 Renewal, 60 days before expiration (non-renewal) in 12.1 Notices). Which provision should be treated as the applicable notice period rule?"

## GET `/api/clarifications`

| Param | Meaning |
|---|---|
| `contract_id` | Optional |
| `status` | `open` / `resolved` / `dismissed` |

Latest versions only. Response `200`: `{"items": [Clarification, ...]}`, oldest first.

## POST `/api/clarifications/{clarification_id}/resolve`

Choose one option:

```json
{ "action": "select", "entity_id": "itm_globex_notice_90", "note": "Section 3.2 governs per legal" }
```

Enter a value not among the options (for `missing`, or when every option is wrong):

```json
{ "action": "custom", "value": { "date": "2027-06-30", "date_text": "per amendment" }, "note": "..." }
```

Dismiss (e.g. a false-positive conflict, where both items are correct and both are kept):

```json
{ "action": "dismiss", "note": "Both notice periods apply to different events" }
```

Effects (one transaction):

| action | Effect |
|---|---|
| `select` | Selected item → `approved`. Other options → `rejected`. One `reviews` row per item, with `clarification_id` set. |
| `custom` | All options → `rejected`. A new extracted item is created with the given value, `confidence: "high"`, `review_status: "edited"`, and no citation. Its `original_value` is the custom value and `origin` is `"human"`. |
| `dismiss` | Item statuses unchanged. The question is closed. For a dismissed conflict, the renewal stays `blocked_by_conflict` until the user rejects all but one item. |

After `select` or `custom`, `status → resolved`. `resolution` stores what was chosen,
separately from the extraction. The renewal and dependent obligation due dates are
recalculated.

Response `200`:

```json
{ "clarification": { /* updated */ }, "renewal": { /* recalculated Renewal or null */ } }
```

Errors: `CLARIFICATION_NOT_FOUND`, `CLARIFICATION_ALREADY_CLOSED` (409),
`VALIDATION_ERROR` (`entity_id` not one of the options, or `value` has the wrong shape).
