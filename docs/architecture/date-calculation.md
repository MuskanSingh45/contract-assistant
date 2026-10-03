# Deterministic Date Calculation

All authoritative dates are calculated in `backend/utils/dates.py`. This is pure Python
with no I/O and no LLM, and is unit-tested. The LLM only supplies the rules (numbers,
units, anchors, date text). The frontend only formats the results.

Libraries: `datetime`, `dateutil.relativedelta` (month/year arithmetic),
`dateutil.parser` (cross-checking date text).

"Today" is passed in as a parameter (`today: date`) so that tests are deterministic. The
API uses the server's local date.

## 1. Inputs and which item is used

For each single-valued field (`effective_date`, `expiration_date`, `initial_term`,
`renewal_terms`, `notice_period`) the calculation uses the one extracted item whose
`review_status != rejected`, with its **current** `value` (so human edits are used).

| Situation | Result |
|---|---|
| exactly one non-rejected item | use it |
| no item | input missing |
| two or more non-rejected items with different values | `calculation_status = blocked_by_conflict`, and dates depending on that field are `null` |

For `notice_period`, only items with `anchor` set to `expiration_date` or `renewal_date` are
renewal-relevant. Items anchored to `other` (e.g. 30 days' notice to terminate for breach)
never drive the renewal deadline. `purpose` is informational only, because the model may
label "terminated by notice 90 days before expiration" as either termination or non-renewal.

The calculation uses unreviewed (`pending`) items, because otherwise nothing would show
until a human reviewed everything. The renewal's `inputs_reviewed` flag tells the UI
whether all inputs are approved/edited.

## 2. Expiration date

1. If an `expiration_date` item exists, use it (`expiration_source = explicit`).
2. Otherwise, if `effective_date` and `initial_term` both exist, expiration = effective + term (`expiration_source = calculated`).
3. If both 1 and 2 are possible and they disagree, this is a conflict on `expiration_date`. A clarification is created and the status is `blocked_by_conflict`.
4. Otherwise expiration is `null`, the status is `incomplete`, and the note is "No expiration date or initial term found".

## 3. Current term end (auto-renewal roll-forward)

```text
if renewal_type == "automatic" and renewal period known and expiration < today:
    current_term_end = expiration + k × period, with the smallest k ≥ 1 such that the result ≥ today
else:
    current_term_end = expiration
```

Each candidate is calculated from the original expiration (`expiration + relativedelta(months=12*k)`),
not by chaining steps, so month-end clamping does not drift.

## 4. Notice deadline

```text
anchor_date = current_term_end   (anchor "expiration_date" or "renewal_date"; same date for the MVP)
notice_deadline = anchor_date − notice period
```

| unit | arithmetic |
|---|---|
| `days` | `anchor − timedelta(days=n)` |
| `months` | `anchor − relativedelta(months=n)` (clamps: 2027-03-31 − 1 month = 2027-02-28) |
| `business_days` | step back n weekdays (Mon–Fri). **Public holidays are ignored**, and `calculation_note` says so. |

- Meaning: `notice_deadline` is the **last day on which notice can be given** ("at least N days before"). The UI label is "Notice due by".
- `anchor = "other"` → `notice_deadline = null`, `incomplete`, note "Notice period is not anchored to the expiration date".
- `notice_deadline` may be in the past (the window was missed for this term). It is still shown, and `days_until_notice_deadline` is negative.

**Reference example (Acme):** expiration 2027-01-31, notice 90 days → `2026-11-02`.

## 5. Lifecycle status (contract)

`UPCOMING_WINDOW_DAYS` defaults to 60.

| Status | Rule (first match wins) |
|---|---|
| `unknown` | no `current_term_end` |
| `expired` | `current_term_end < today` (only possible when not auto-renewing) |
| `expiring_soon` | `notice_deadline` (or `current_term_end` if there is no deadline) is between today and today + `UPCOMING_WINDOW_DAYS` |
| `active` | otherwise |

## 6. Obligation due dates

The model extracts `due_rule = {"basis", "offset_days"}` and, for explicit dates,
`due_date_text`.

| `basis` | `due_date` | `due_date_source` |
|---|---|---|
| `explicit_date` | parsed `due_date_text` | `explicit` |
| `effective_date_anniversary` | next date ≥ today of `effective + k × period + offset_days` (period from `frequency`) | `calculated` |
| `calendar_period_end` | end of the most recent calendar month/quarter/year (per `frequency`) + `offset_days`; if that is before today, use the next period's | `calculated` |
| `renewal_notice_deadline` | the renewal's `notice_deadline` | `calculated` |
| `unspecified` | `null` (UI shows `frequency_text`) | `null` |

Rules:

- `frequency = one_time` with `effective_date_anniversary`/`calendar_period_end` → `null` (not meaningful).
- `frequency = other` → `null` unless `explicit_date`.
- Calculated due dates show **the next occurrence only**. There is no recurring schedule table in the MVP.

**Reference examples (today = 2026-10-03):**
- Quarterly report, `calendar_period_end` + 30 → Q3 ends 2026-09-30, so the due date is `2026-10-30`.
- Annual insurance certificate, `effective_date_anniversary` from 2025-01-31 → `2027-01-31`.
- Non-renewal notice, `renewal_notice_deadline` → `2026-11-02`.

## 7. Date text cross-check

For every date the model returns (`date` + `date_text`), the AI validators (`ai/validators/extraction_validator.py`) parse `date_text`
with `dateutil.parser.parse(..., fuzzy=False)`.

- If it parses to a different date than `date` → set confidence to `low` and add an ambiguity note "Model date does not match quoted text".
- If it does not parse (e.g. "the first business day of the year") → keep the model's `date` with confidence at most `medium`.

## 8. When recalculation happens

- At the end of analysis (stage `analyzing`).
- In the same request as any review action or clarification resolution that touches an input item (sections 1 and 6).
- `days_until_*` and `lifecycle_status` are computed at **read time**, because they depend on today. The stored `renewals` row holds only the date results.
