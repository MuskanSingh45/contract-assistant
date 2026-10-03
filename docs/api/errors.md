# API Errors

Every error response has this shape:

```json
{
  "error": {
    "code": "INVALID_DOCUMENT",
    "message": "Unsupported document format. Upload a PDF or DOCX file.",
    "details": null,
    "request_id": "req_82488e9c75c3"
  }
}
```

- `code` is stable and machine-readable. The frontend switches on it.
- `message` is human-readable and may be shown to the user.
- `details` is optional (object or `null`). For `VALIDATION_ERROR` it lists field problems: `{"fields": [{"field": "value.date", "problem": "not a valid date"}]}`.
- `request_id` is the ID of the request that failed, the same value as the `X-Request-ID` response header. Quote it when reporting a problem: every server log line for that request carries it (see below).
- FastAPI's default `422` validation responses must be converted to this shape (`VALIDATION_ERROR`).

## Request IDs

Every response, success or error, has an `X-Request-ID` header. The backend generates
`req_<12 hex>`, or reuses a client-sent `X-Request-ID` if it is 1–64 characters of
`[A-Za-z0-9._-]`. The ID appears in every log line written while handling the request,
including the background analysis started by `POST /contracts/{id}/analyze`. The frontend
shows it as **Reference** on error screens. Logging details: [backend architecture](../architecture/backend-architecture.md#logging).

## Codes

| Code | HTTP | When |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body/query does not match the documented shape |
| `INVALID_DOCUMENT` | 415 | Not a PDF/DOCX (by extension or file signature) |
| `EMPTY_UPLOAD` | 400 | No file, or 0-byte file |
| `FILE_TOO_LARGE` | 413 | Larger than `MAX_UPLOAD_MB` |
| `DUPLICATE_VERSION` | 409 | New version has the same file hash as the latest version |
| `CONTRACT_NOT_FOUND` | 404 | |
| `VERSION_NOT_FOUND` | 404 | |
| `OBLIGATION_NOT_FOUND` | 404 | |
| `ITEM_NOT_FOUND` | 404 | Review target (`entity_type` + `entity_id`) does not exist |
| `CITATION_NOT_FOUND` | 404 | |
| `CLARIFICATION_NOT_FOUND` | 404 | |
| `CLARIFICATION_ALREADY_CLOSED` | 409 | Resolving a clarification that is not `open` |
| `INVALID_REVIEW_ACTION` | 400 | Unknown action, or `value` missing/present incorrectly |
| `ANALYSIS_IN_PROGRESS` | 409 | Analyze requested while the version is `queued`/`processing` |
| `ANALYSIS_NOT_COMPLETE` | 409 | Requesting results that need a completed analysis |
| `AI_UNAVAILABLE` | 503 | Ollama unreachable or model not pulled |
| `NOT_FOUND` | 404 | Unknown route |
| `METHOD_NOT_ALLOWED` | 405 | Known route, wrong HTTP method |
| `INTERNAL_ERROR` | 500 | Unexpected. The message is generic; the traceback is in the server log only, under the `request_id`. |

## Client-side codes

The frontend's `ApiError` (`frontend/src/lib/api.js`) adds codes for failures that never reach the backend:

| Code | When |
|---|---|
| `NETWORK_ERROR` | The backend cannot be reached (not running, wrong `VITE_API_BASE_URL`, CORS) |
| `TIMEOUT` | No response within 30 s (uploads: 120 s) |
| `REQUEST_FAILED` | A 4xx without the documented body (e.g. from a proxy) |

## Analysis failure codes

These are not HTTP responses. Analysis runs in the background, so these codes appear in
`GET /api/contracts/{id}/analysis` → `error.code` when `analysis_status = "failed"`.

| Code | Stage | When |
|---|---|---|
| `DOCUMENT_PARSE_FAILED` | parsing | File is corrupt, encrypted, or cannot be opened |
| `NO_EXTRACTABLE_TEXT` | parsing | Parsed successfully but contains no text (e.g. scanned PDF; OCR is out of scope) |
| `AI_UNAVAILABLE` | extracting | Ollama stopped responding during analysis |
| `AI_TIMEOUT` | extracting | A model call exceeded `OLLAMA_TIMEOUT_SECONDS` |
| `INVALID_AI_OUTPUT` | extracting | Output failed JSON/schema validation after the retry |
| `ANALYSIS_FAILED` | any | Any other failure |

`CITATION_VALIDATION_FAILED` is **not** an error. A quote that cannot be located is not a
reason to fail the analysis. The item is kept with `validation_status: "not_found"` and its
confidence is forced to `low`. See [../ai/citation-and-review.md](../ai/citation-and-review.md).
