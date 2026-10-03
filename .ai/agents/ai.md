# Agent: AI Pipeline (Claude)

**Owns:** `ai/`, `contracts/`, `tests/ai/`, `scripts/evaluate_ai.py`.

**Read first:** `docs/ai/` (all), `docs/decisions/007-deterministic-conflicts-and-citations.md`, `docs/architecture/date-calculation.md` §7.

**Interface to the backend** (`ai/pipeline/orchestrator.py`):
```python
def analyze(segments: list[Segment], *, on_progress: Callable[[str, int, int], None] | None = None, client=None) -> AnalysisResult
# Types in ai/types.py. on_progress: ("extracting", i, n) 1-based per window, then ("validating", 0, 0).
# AnalysisResult: items, obligations, clarifications (option_indexes into items), model_name, prompt_version, stats
# Raises AIUnavailable, AITimeout, InvalidAIOutput (mapped to error codes by the backend)
```

**Must:**
- Set Ollama `format` = schema, `think=false`, `num_ctx` from env, `temperature=0`. Refuse prompts larger than 75% of `num_ctx`.
- Validate against schema (one retry), then citations, then business rules, then adjust confidence (downgrade only).
- Keep conflict detection and clarification text deterministic.
- Version prompts (`# version:` header). Re-run the evaluation after every prompt or schema change.

**Must not:** compute dates, output page numbers, access the DB, or add LLM calls for conflicts or summaries.
