# ADR 007 — Deterministic Conflict Detection and Citation Grounding

## Status
Accepted (2026-10-03).

## Context
The original plan used separate LLM calls for conflict detection, clarification generation
and summarization. With a local 8B model and limited time, each extra LLM step adds latency
and another place for the model to make things up.

## Decision
- **Conflicts are detected in code:** two or more non-rejected candidates with different normalized values for a single-valued field. Because extraction runs per text window, contradictory clauses in different sections naturally produce separate candidates.
- **Ambiguity comes from extraction itself:** each extracted item may carry an `ambiguity_note`. No separate ambiguity prompt is used.
- **Clarification questions use templates** in the backend, not LLM text.
- **Citations are grounded:** the model cites a segment label (`S12`) and a verbatim quote. The backend checks that the quote exists in that segment (exact, then fuzzy) and copies page/section from the stored segment. The model never outputs page numbers.
- **Summarization is deferred** (not in the MVP).

## Consequences
The MVP needs two prompts: `terms` and `obligations`. Conflict and citation behaviour is
unit-testable without a model. Subtle semantic conflicts (e.g. a notice clause that only
applies to termination for cause) may be missed. Those are mitigated by `ambiguity_note`
and human review.
