# Conflict Detection

Deterministic code (`ai/pipeline/conflict_detection.py`), run after merging candidates
across windows. No LLM call. See [ADR 007](../decisions/007-deterministic-conflicts-and-citations.md).

## Rule

For each **single-valued** field (`effective_date`, `expiration_date`, `initial_term`,
`renewal_terms`, `notice_period`): if there are two or more candidates with different
normalized values, that is a **conflict**.

`party` and `termination_clause` are multi-valued and never conflict.

There is one cross-field conflict: an explicit `expiration_date` ≠ `effective_date` +
`initial_term` is a conflict on `expiration_date`. It is checked by the backend during date
calculation, because it needs date arithmetic.

## Behaviour

1. Keep **all** candidates as separate extracted items, each with its own citations.
2. Create a `clarification_question` (`kind = conflict`) with those items as options, and attach their citations to the question.
3. Dependent calculations return `blocked_by_conflict`. Nothing is chosen silently.
4. A human resolves it ([clarification.md](clarification.md)).

Example: notice period 90 days (§3.2) vs 60 days (§12.1) produces two `notice_period` items,
one open clarification, and a renewal with `notice_deadline = null`.

## Limits (accepted for the MVP)
Semantic conflicts that produce the same field value, or clauses that apply to different
events, are not detected by this rule. The extraction prompt asks the model to record such
cases in `ambiguity_note`.

For `notice_period`, the rule compares only **renewal-relevant** items: those with `anchor`
equal to `expiration_date` or `renewal_date`. A 30-day notice to terminate for breach
(`anchor: other`) does not conflict with a 90-day non-renewal notice. `purpose` is **not**
used for grouping, because the model may label the same kind of clause either way.

The conflict detector makes no legal conclusions.
