# Prompt Design

## Prompts in use

| File | Version | Used by | Output schema |
|---|---|---|---|
| `ai/prompts/extraction/terms.txt` | `terms-v2` | `ai/pipeline/extraction.py` | `ai/schemas/extraction.json` |
| `ai/prompts/extraction/obligations.txt` | `obligations-v2` | `ai/pipeline/obligation_extraction.py` | `ai/schemas/obligation.json` |

Both run once per text window, with either provider (Ollama locally, Groq online). Conflict
detection, clarification questions and date arithmetic have **no prompts**: they are
deterministic code ([ADR 007](../decisions/007-deterministic-conflicts-and-citations.md)).
Summarization is deferred.

## Techniques used

| Technique | How it appears in the prompts | Why |
|---|---|---|
| **Role and scope framing** | "You extract contract terms for an information-management tool. You do not give legal advice." | Bounds the task and the tone; no interpretation of legal effect |
| **Closed-world grounding** | "Use ONLY the text in the segments below. Never use outside knowledge or assume typical contract terms." | Stops the model filling gaps with boilerplate it has seen elsewhere |
| **Structured input with stable IDs** | Each segment is rendered as `[S12] (section heading) text`; the model cites `segment_id` | Lets code resolve the page and section and verify every quote; the model never outputs page numbers |
| **Mandatory verbatim evidence** | Every candidate needs `segment_id` + an exact quote (max 300 characters) | Enables citation validation; unsupported candidates are dropped by code |
| **Explicit abstention** | "If the information is not stated, return an empty list []. An empty list is a correct and expected answer." | Makes "not found" a valid answer instead of an invented one (checked by `missing_info_correct`) |
| **Conflict preservation** | "If two clauses state different values, return BOTH. Never choose between them." | The choice belongs to a person; code turns it into a clarification question |
| **No arithmetic** | "Do NOT calculate dates." Expiration written as a duration goes to `initial_term`, not `expiration_date` | All date logic is deterministic and unit-tested (`backend/utils/dates.py`) |
| **Enumerated value spaces** | `anchor`, `purpose`, `frequency`, `due_rule.basis` are closed enums with definitions | Maps free text onto values the date engine understands |
| **Contrastive few-shot examples** | Paired examples, e.g. "notice … before the end of the term" → `anchor: expiration_date` vs "terminate upon 15 days' notice if the other party breaches" → `anchor: other` | Teaches the boundaries the evaluation found hardest |
| **Negative definitions** | "Rights and permissions ('may', 'is entitled to') are NOT obligations" | Separates duties from permissions. The prompt alone was not enough: evaluation run 1 still turned "Customer may inspect" into an obligation, so a deterministic check now drops such candidates ([pipeline.md](pipeline.md) §4) |
| **Calibrated self-report** | `confidence` high / medium / low with definitions; `ambiguity_note` for conditional or unclear clauses | Feeds the review queue; code still lowers confidence when a quote cannot be verified |
| **Schema-constrained decoding** | The JSON Schema is passed as Ollama `format` or Groq `response_format: json_schema` | Valid JSON by construction; `jsonschema` validation plus one repair retry catches the rest |
| **Deterministic decoding** | `temperature: 0`, `seed: 42` | Reproducible results for evaluation and debugging |
| **Reasoning suppressed** | Ollama `think: false` (+ `/no_think`); Groq returns plain JSON | No `<think>` text in the output, faster calls; `clean_content()` strips it if it ever appears |

## What every prompt must require
1. Extract only information stated in the supplied segments.
2. Return JSON matching the schema (also enforced by the provider's structured-output mode).
3. Cite each candidate with a segment label and a **verbatim** quote.
4. Return `[]` when information is absent. Never guess.
5. Return all contradictory candidates, and never choose.
6. Report confidence and an `ambiguity_note` when unsure.
7. Never perform date arithmetic or output page numbers.

## What code does after the model
The prompt is one layer; the guarantees come from code ([pipeline.md](pipeline.md)):
schema validation with one repair retry → citation validation (segment exists, quote found,
fuzzy match for whitespace) → grounding checks (the value must be supported by its own quote,
e.g. "every two weeks" cannot become a 2-day notice period) → business validation → merge
across windows → deterministic conflicts, clarifications and dates.

## Template variables
Prompts are plain text with `{{segments}}` (the formatted window). Nothing else is
interpolated.

## Versioning and evaluation
Each prompt file starts with `# version: <name>-vN`. The analysis records `prompt_version` as
`terms-vN+obligations-vM` on the contract version. Any prompt change bumps the version and
must be re-run through `scripts/evaluate_ai.py` (`make eval`; add `LLM_PROVIDER=groq` for the
hosted model). Record the before/after metrics in [../testing/ai-evaluation.md](../testing/ai-evaluation.md).
A change that increases `hallucinated_values` or `rights_as_obligations` is not merged.
