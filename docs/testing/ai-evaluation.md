# AI Evaluation

## Run

```bash
.venv/bin/python scripts/evaluate_ai.py                    # all samples, about 2 min each on an M1 Pro
.venv/bin/python scripts/evaluate_ai.py acme-services-agreement
.venv/bin/python scripts/evaluate_ai.py --rescore ai/evaluation/results/<file>.json   # re-score without the model
```

Each sample runs through the **same code path as the app**: parse → `ai` pipeline → persist into a
temporary SQLite database → deterministic date calculation, with the fixture's `evaluation_date`
as "today". The script then scores the result against
`contracts/fixtures/expected-extractions/<name>.json` (format: `contracts/README.md`).
Results are saved to `ai/evaluation/results/<timestamp>.json` (git-ignored), including the raw
outputs, so the scoring can be re-run with `--rescore`.

Code: `ai/evaluation/metrics.py` (pure scoring, unit-tested in `tests/ai/evaluation/`),
`ai/evaluation/evaluator.py` (fixtures and aggregation), `scripts/evaluate_ai.py` (runner and report).

## Samples

| Sample | Tests |
|---|---|
| simple / acme-services-agreement | clean contract: explicit dates, auto-renewal, 90-day notice, calendar-quarter obligation |
| conflicting / globex-hosting-agreement | 90 vs 60 day notice → conflict clarification, blocked deadline |
| renewal / northstar-software-subscription | term given as "two years" (calculated expiration), 30 **business** days notice |
| ambiguous / meridian-consulting-agreement | no fixed term, "reasonable notice": must return `[]`, not invent values; `missing` clarification |
| multiple-obligations / harbor-logistics-agreement | 7 obligations, explicit due date, rights ("may inspect", "may suspend") that must not become obligations |

## Metrics

| Metric | Definition |
|---|---|
| `field_recall_pct` | required expected values found / (found + missing) |
| `field_precision_pct` | found / (found + unexpected extracted values). Unexpected values are potential hallucinations. |
| `hallucinated_values` | extracted values matching no expected value (including optional ones) |
| `missing_info_correct` | fields expected `[]` that came back `[]` (the "don't invent" check) |
| `obligation_recall_pct` | required obligations matched by `description_contains` |
| `obligation_attribute_accuracy_pct` | responsible party / frequency / due rule correct on matched obligations |
| `rights_as_obligations` | obligations matching a `must_not_contain_obligations` term |
| `conflict_detection_ok` | samples whose conflict clarifications exactly match the fixture |
| `date_results_ok` | samples whose renewal and obligation due dates (calculated by code) all match |
| `citations_verified_pct`, `citations_not_found` | citation grounding quality |

## Results log

| Date | Model / prompts | Precision | Hallucinated | Missing-info correct | Rights as obligations | Conflicts | Dates | Citations verified |
|---|---|---|---|---|---|---|---|---|
| 2026-10-03 run 1 | qwen3:8b, terms-v2+obligations-v2 | 90.9% | 3 | 8/10 | 1 | 5/5 | 5/5 | 100% |
| 2026-10-03 run 2 (after grounding checks + fixture corrections) | same | **100%** | **0** | **9/9** | **0** | 5/5 | 5/5 | 100% |

Run 1 errors: Meridian "every two weeks" was extracted as a 2-day notice period; Harbor "Customer **may** inspect" was extracted as an obligation. Both are now blocked by deterministic checks (docs/ai/pipeline.md §4). Two other flags were fixture mistakes: Acme's 30-day breach notice was a correct extraction, and Globex's termination summary was acceptable.
Field and obligation recall were 100% in both runs. Average time was about 80 s per contract on an M1 Pro.

Caveat: 5 short synthetic contracts. This shows the guards work; it does not prove accuracy on long real-world contracts.

## When to run
After any change to a prompt, schema, `OLLAMA_MODEL` or validator. Record the summary in the
task log. A change that increases `hallucinated_values` or `rights_as_obligations` is not merged.
