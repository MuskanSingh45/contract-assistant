# Confidence

`confidence` is the AI's confidence in an extraction: `high`, `medium` or `low`.
It is not legal certainty and not human approval.

`review_status` is the human workflow state: `pending`, `approved`, `edited` or `rejected`.
`confidence = high` with `review_status = pending` is normal. It means the AI is
confident, but no human has checked the item yet.

## Where confidence comes from

1. The model reports it per candidate.
2. `ai/validators/confidence_validator.py` can only **lower** it:

| Condition | Maximum confidence |
|---|---|
| All citations `not_found` | low |
| Model `date` disagrees with parsed `date_text` | low |
| Best citation is `approximate` | medium |
| `ambiguity_note` is set | medium |
| `date_text` not parseable as a calendar date | medium |

Reviews never change `confidence`. Human edits set `review_status = edited`, and the UI
shows "Edited by reviewer" instead of the AI confidence for the edited value.

## UI
Use badges with three colours. The Review queue sorts `low` first.
