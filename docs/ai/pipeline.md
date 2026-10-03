# AI Pipeline

The backend's `analysis_service` drives the pipeline. `ai/pipeline/orchestrator.py` is
called with the parsed segments and returns validated candidates. The `ai/` package has
no database access.

```text
segments (from backend/documents)
   ↓
windowing                         ai/pipeline/orchestrator.py
   ↓  per window
terms extraction                  ai/pipeline/extraction.py            prompt: extraction/terms.txt
obligation extraction             ai/pipeline/obligation_extraction.py prompt: extraction/obligations.txt
   ↓
JSON Schema validation (+1 retry) ai/llm/structured_output.py, ai/validators/extraction_validator.py
   ↓
citation validation               ai/validators/citation_validator.py
   ↓
confidence adjustment             ai/validators/confidence_validator.py
   ↓
merge across windows              ai/pipeline/orchestrator.py
   ↓
conflict detection                ai/pipeline/conflict_detection.py   (deterministic)
   ↓
clarification questions           ai/pipeline/clarification.py        (templates)
   ↓  returned to backend
date calculation                  backend/utils/dates.py
version comparison                backend/services/version_service.py
persist (one transaction)         backend/services/analysis_service.py
   ↓
human review
```

## 1. Segments

`backend/documents/` produces ordered segments:
`{seq, page | null, section | null, text}`.

- PDF: per page, split into paragraphs/blocks. DOCX: paragraphs. Segments are 1,500 characters or less (long paragraphs are split at sentence boundaries).
- `section` = the nearest preceding heading. Headings are detected by DOCX heading styles, or for PDF by a line matching a numbered heading (`^\d+(\.\d+)*\.?\s+\S`) or a short all-caps line.
- Normalization: collapse whitespace, rejoin words hyphenated across line breaks, convert curly quotes to straight quotes. The **normalized** text is stored and used for both the model and citation validation, so offsets match.

## 2. Windowing

Segments are packed in order into windows of at most `EXTRACTION_WINDOW_TOKENS` (default
6,000; estimated as characters ÷ 4). Segments are never split across windows. Each segment
is shown to the model as:

```text
[S12] (2.2 Renewal)
This Agreement shall automatically renew for ...
```

Page numbers are **not** shown to the model, and the model never returns them.

Most short contracts fit in one window. Long contracts take several windows and therefore
several model calls; progress is reported as `progress.current/total`.

## 3. Extraction

Two calls per window, both with Ollama `format` set to the JSON Schema in `ai/schemas/`:

| Call | Schema | Extracts |
|---|---|---|
| terms | `ai/schemas/extraction.json` | parties, effective/expiration date, initial term, renewal terms, notice period, termination clause |
| obligations | `ai/schemas/obligation.json` | obligations with responsible party, frequency, due rule |

Output format details: [extraction.md](extraction.md).

## 4. Validation

1. **Schema**: parse JSON and validate against the schema. On failure, retry once with the validator error appended to the prompt. A second failure fails the analysis with `INVALID_AI_OUTPUT`. Never persist partially valid output.
2. **Citation**: see [citation-and-review.md](citation-and-review.md).
3. **Business**: enums are valid, numbers are positive, dates are real calendar dates, `date` matches `date_text` (see [../architecture/date-calculation.md](../architecture/date-calculation.md) §7). Invalid candidates are dropped and logged.
4. **Extra grounding checks** (added after testing on qwen3:8b):
   - `initial_term` is dropped unless the cited text (±150 characters) mentions its unit. This stops the model inventing a term from the start and end dates.
   - A `notice_period` anchored to expiration/renewal is re-anchored to `other` (with a note) if the cited text never mentions expiry, renewal or "term". This prevents false conflicts with breach notices.
   - A `notice_period` is dropped unless its cited text contains both the number (digits or words) and the unit. Without this, "a report every two weeks" was read as a 2-day notice.
   - A `renewal_terms` period not stated in the cited text is cleared, with a note. The type is kept.
   - An obligation whose quotes only say "may" (with no shall/must/will/agrees) is dropped, because it is a right, not an obligation.
   - Party roles are normalized (`service_provider` becomes `service provider`). Dropped candidates are counted in `stats.dropped_invalid`.
5. **Confidence**: adjusted downward by the rules in [confidence.md](confidence.md). It is never raised.

## 5. Merge across windows

Candidates for the same field with the **same normalized value** become one item. Their
citations are unioned and the highest confidence is kept. Candidates with different values
stay separate. That is how conflicts surface.

Normalization for comparison: dates as ISO strings; periods as `(value, unit)` (no unit
conversion, so 3 months ≠ 90 days and that is flagged); parties by lowercase name without
punctuation or a trailing "inc/ltd/llc/corp".

## 6. Conflicts and clarifications

Deterministic, with no LLM: see [conflict-detection.md](conflict-detection.md) and
[clarification.md](clarification.md).

## 7. Hard rules

- No model output reaches the database without passing schema, citation and business validation.
- The model does no authoritative date arithmetic. Its `date` fields are only normalizations of quoted date text.
- When no model service is available, the analysis fails visibly (`AI_UNAVAILABLE` / `AI_TIMEOUT`). Results are never fabricated. A configured fallback provider (`LLM_FALLBACK_PROVIDER`) is a different real model running the same pipeline, not a substitute result ([model-config.md](model-config.md)).
- Every analysis records `model_name` and `prompt_version` on the version.
