# Clarification

A clarification question is created when the system cannot safely decide something on its
own. Code in `ai/pipeline/clarification.py` creates it, and the question text comes from a
**template**. No LLM is used.

| kind | Trigger | Template |
|---|---|---|
| `conflict` | [conflict-detection.md](conflict-detection.md) | "Two sections specify different {field label}s ({value A} in {section A}, {value B} in {section B}). Which provision should be treated as the applicable {field label} rule?" |
| `ambiguity` | A date-input item (`effective_date`, `expiration_date`, `initial_term`, `renewal_terms`, `notice_period`) has an `ambiguity_note` | "The {field label} may be ambiguous: {ambiguity_note}. Please confirm or correct the extracted value '{display_value}'." |
| `missing` | Neither `expiration_date` nor `initial_term` was found | "No expiration date or initial term was found. Enter the expiration date to enable deadline calculation, or dismiss if the contract has no fixed term." |

Rules:
- Show the relevant source evidence (the question's citations, and each option's citations).
- Do not invent an answer.
- Persist the question, its options and its status.
- Resolution is recorded separately (`resolution_json`, `resolution_note`), and the original extraction stays unchanged.
- Resolving it updates item review statuses (with linked `reviews` rows) and triggers recalculation.

Ambiguity questions on non-date fields are not created. Those items only show their
`ambiguity_note` in the review queue.

API: [../api/clarifications.md](../api/clarifications.md).
