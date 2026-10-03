# Contract Samples and Fixtures

Ground truth for AI evaluation (`scripts/evaluate_ai.py`) and demos. These are synthetic
contracts with no real parties.

```text
samples/
  simple/                 clean contract, everything calculable      (acme-services-agreement)
  conflicting/            contradictory clauses → clarification      (globex-hosting-agreement)
  renewal/                term given as a length, business-day notice (northstar-software-subscription)
  ambiguous/              no fixed term, vague "reasonable notice"   (meridian-consulting-agreement)
  multiple-obligations/   7 obligations + rights that are NOT obligations (harbor-logistics-agreement)
fixtures/
  expected-extractions/   one <sample-name>.json per sample
```

Each sample also has a generated `.pdf` and `.docx` for upload demos
(`.venv/bin/python tests/backend/documents/make_samples.py` regenerates them).
Samples are `.txt` so they can be fed straight to the pipeline through
`backend/documents/text_parser.py`. For the demo upload, export the same text to PDF/DOCX.
The upload API accepts only PDF/DOCX.

## Expected file format

- `fields.<field_name>`: the expected candidate **values** after merging. Segment ids are not compared (they depend on segmentation). Keys present are compared exactly; `optional: true` means a missing candidate is not an error, but a wrong value still is.
- `obligations`: matched by `description_contains` (case-insensitive, all terms). `optional` obligations are neither required nor penalized.
- `must_not_contain_obligations`: terms that must not appear in any obligation description. This catches rights extracted as obligations.
- `conflicts`: expected clarification questions of kind `conflict`.
- `clarifications`: other expected clarification kinds, e.g. `[{"kind": "missing"}]`.
- `renewal` / `obligation_due_dates`: expected deterministic results, with `evaluation_date` as "today".

The `simple` and `conflicting` samples match the demo data in `db/seeds/development.sql`.
