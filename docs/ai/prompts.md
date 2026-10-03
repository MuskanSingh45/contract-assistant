# Prompt Design

## MVP prompts

| File | Used by | Schema |
|---|---|---|
| `ai/prompts/extraction/terms.txt` | `ai/pipeline/extraction.py` | `ai/schemas/extraction.json` |
| `ai/prompts/extraction/obligations.txt` | `ai/pipeline/obligation_extraction.py` | `ai/schemas/obligation.json` |

Conflict detection, clarification and summary have **no prompts**. Conflicts and
clarifications are deterministic ([ADR 007](../decisions/007-deterministic-conflicts-and-citations.md)),
and summarization is deferred.

## Every prompt must require the model to
1. Extract only information stated in the supplied segments.
2. Return JSON matching the schema. (Ollama also enforces this with `format`.)
3. Cite each candidate with a segment label and a **verbatim** quote.
4. Return `[]` when information is absent. Never guess.
5. Return all contradictory candidates, and never choose.
6. Report confidence and an `ambiguity_note` when unsure.
7. Never perform date arithmetic or output page numbers.

## Template variables
Prompts are plain text with `{{segments}}` (the formatted window). Nothing else is
interpolated.

## Versioning
Each prompt file starts with a line `# version: terms-v1`. The analysis records
`prompt_version` as `terms-vN+obligations-vM` on the version. Any prompt change bumps the
version and must be re-run through `scripts/evaluate_ai.py`. Record the before/after
metrics in the task log.
