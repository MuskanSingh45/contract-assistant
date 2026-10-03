# Renewals API

A renewal is the **calculated** result for one contract version. The backend produces it
from that version's extracted items (effective date, expiration date, initial term,
renewal terms, notice period). It is not AI output and it is not reviewed directly. To
change it, review or edit the underlying extracted items or resolve the clarification. The
backend then recalculates it immediately.

## Renewal object

```json
{
  "contract_id": "ctr_acme",
  "contract_name": "Acme Services Agreement",
  "contract_version_id": "ver_acme_1",
  "effective_date": "2025-01-31",
  "expiration_date": "2027-01-31",
  "expiration_source": "explicit",
  "renewal_type": "automatic",
  "renewal_period": { "value": 12, "unit": "months" },
  "current_term_end": "2027-01-31",
  "notice_period": { "value": 90, "unit": "days", "anchor": "expiration_date" },
  "notice_deadline": "2026-11-02",
  "days_until_notice_deadline": 30,
  "days_until_term_end": 120,
  "lifecycle_status": "expiring_soon",
  "calculation_status": "calculated",
  "calculation_note": null,
  "inputs_reviewed": false,
  "input_item_ids": ["itm_acme_eff", "itm_acme_exp", "itm_acme_ren", "itm_acme_notice"]
}
```

- `notice_deadline` is the **last day** on which notice can be given ("at least 90 days before").
- `expiration_source`: `explicit` means the date came from the contract. `calculated` means it was derived as effective date + initial term.
- `current_term_end`: equals `expiration_date`, unless the contract auto-renews and the expiration date has passed. Then it is rolled forward by whole renewal periods.
- `inputs_reviewed`: `true` only when every input item is `approved` or `edited`. The UI should mark deadlines built on unreviewed data (e.g. "Based on unreviewed data").
- `calculation_status`:
  - `calculated`: all needed inputs are present and unambiguous.
  - `incomplete`: an input is missing (e.g. no expiration date) or not calculable (`anchor: "other"`). `calculation_note` says which. The deadline is `null`.
  - `blocked_by_conflict`: an input has an open clarification. The deadline is `null` until a human resolves it. The system never picks one silently.

Example of a blocked renewal (seed contract Globex):

```json
{
  "contract_id": "ctr_globex",
  "notice_period": null,
  "notice_deadline": null,
  "days_until_notice_deadline": null,
  "calculation_status": "blocked_by_conflict",
  "calculation_note": "Two notice periods were found (90 days and 60 days). Resolve the clarification question to calculate the notice deadline."
}
```

## GET `/api/renewals`

One renewal per contract (latest version). Contracts whose analysis has not completed are
omitted.

| Param | Meaning |
|---|---|
| `within_days` | Only renewals whose `notice_deadline` (or `current_term_end` when there is no deadline) is within N days from today |
| `calculation_status` | Filter by calculation status |

Response `200`: `{"items": [Renewal, ...]}`, sorted by `notice_deadline` ascending, nulls last.
