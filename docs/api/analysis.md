# Analysis API

Analysis runs per **version**, in the background (FastAPI `BackgroundTasks`; no queue
infrastructure for the MVP). The frontend polls for progress.

## POST `/api/contracts/{contract_id}/analyze`

Request body (optional):

```json
{ "version_id": "ver_acme_1" }
```

Default: latest version. Re-analyzing a version that is `completed` or `failed` is allowed.
It deletes that version's previous extracted items, obligations, citations, clarifications,
renewal and changes, then runs again. Review history (`reviews`) is kept.

Response `202`:

```json
{
  "contract_id": "ctr_acme",
  "version_id": "ver_acme_1",
  "analysis_status": "queued"
}
```

Errors: `CONTRACT_NOT_FOUND`, `VERSION_NOT_FOUND`, `ANALYSIS_IN_PROGRESS` (409, version is
`queued`/`processing`), `AI_UNAVAILABLE` (503, Ollama unreachable or model not pulled;
checked before queuing).

## GET `/api/contracts/{contract_id}/analysis`

Query: `version_id` (optional, default latest).

Response `200`:

```json
{
  "contract_id": "ctr_acme",
  "version_id": "ver_acme_1",
  "analysis_status": "processing",
  "analysis_stage": "extracting",
  "progress": { "current": 2, "total": 4 },
  "error": null,
  "started_at": "2026-09-28T09:00:05Z",
  "completed_at": null,
  "summary": null
}
```

When `analysis_status = "completed"`:

```json
{
  "analysis_status": "completed",
  "analysis_stage": "complete",
  "progress": null,
  "error": null,
  "summary": {
    "extracted_items": 6,
    "obligations": 3,
    "pending_reviews": 9,
    "open_clarifications": 0,
    "citations_not_found": 0,
    "renewal_calculation_status": "calculated"
  }
}
```

When `analysis_status = "failed"`:

```json
{
  "analysis_status": "failed",
  "analysis_stage": "extracting",
  "error": { "code": "INVALID_AI_OUTPUT", "message": "Model output did not match the extraction schema after 2 attempts." }
}
```

`analysis_stage` on failure is the stage that failed. **A failed analysis persists nothing
partial**: all results for the version are written in one transaction at the end.

- `progress` is only set during `extracting`. It counts text windows sent to the model, so the UI can show "Extracting (2 of 4)".
- Polling: every 2 s while `queued`/`processing`. Expect 1–5 minutes on a laptop.

## Stages

| UI step | Source | `analysis_stage` | What happens |
|---|---|---|---|
| Uploading | client upload progress (`POST /api/contracts`) | — | |
| Parsing | backend | `parsing` | PDF/DOCX → normalized text → segments |
| Extracting | backend | `extracting` | LLM extraction per text window |
| Validating | backend | `validating` | schema, citation and business validation |
| Analyzing | backend | `analyzing` | conflict detection, date calculation, version comparison, persist |
| Complete | backend | `complete` | |

Analysis status is persisted on the version, so the frontend never infers backend state from
UI state. The analysis page route is `/contracts/:id/analyzing`.
