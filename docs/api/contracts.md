# Contracts API

Contract-level display fields (parties, dates, deadlines) are not stored on the contract.
The backend derives them from the **latest version's** extracted items and renewal
calculation. Rejected items are excluded.

## Contract summary object

Used in the contract list and the dashboard.

```json
{
  "id": "ctr_acme",
  "name": "Acme Services Agreement",
  "parties": ["Acme Corporation", "Example Services Ltd."],
  "effective_date": "2025-01-31",
  "expiration_date": "2027-01-31",
  "current_term_end": "2027-01-31",
  "renewal_type": "automatic",
  "notice_deadline": "2026-11-02",
  "days_until_notice_deadline": 30,
  "lifecycle_status": "expiring_soon",
  "latest_version": {
    "id": "ver_acme_1",
    "version_number": 1,
    "analysis_status": "completed"
  },
  "pending_review_count": 8,
  "open_clarification_count": 0,
  "created_at": "2026-09-28T09:00:00Z",
  "updated_at": "2026-09-29T14:10:00Z"
}
```

- Every date field is `null` until analysis completes or if the date was not found.
- `lifecycle_status` is calculated by the backend. See [../architecture/date-calculation.md](../architecture/date-calculation.md).
- `pending_review_count` counts extracted items and obligations with `review_status = pending` in the latest version.

---

## GET `/api/contracts`

Query parameters (all optional):

| Param | Meaning |
|---|---|
| `search` | Case-insensitive match on contract name or party name |
| `lifecycle_status` | One of the `lifecycle_status` enum values |
| `needs_review` | `true` → only contracts with `pending_review_count > 0` or open clarifications |

Response `200`:

```json
{ "items": [ /* Contract summary objects */ ] }
```

Sorted by `updated_at` descending.

---

## POST `/api/contracts`

Uploads a document and creates a contract with **version 1**. It does **not** start
analysis. The frontend then calls `POST /api/contracts/{id}/analyze`, which keeps upload
errors and analysis errors separate.

Request: `multipart/form-data`

| Field | Required | Notes |
|---|---|---|
| `file` | yes | `.pdf` or `.docx`, max 20 MB (`MAX_UPLOAD_MB`). Checked by extension **and** file signature. |
| `name` | no | Contract display name. Default: file name without extension. |

Response `201`:

```json
{
  "contract": { /* Contract summary object, dates null */ },
  "version": { /* Version object, see versions.md, analysis_status "not_started" */ }
}
```

Errors: `INVALID_DOCUMENT` (wrong type/signature), `EMPTY_UPLOAD` (0 bytes / no file),
`FILE_TOO_LARGE`.

Text extraction happens during analysis, not upload. So a scanned (image-only) PDF uploads
fine and then fails analysis with `NO_EXTRACTABLE_TEXT`. OCR is out of scope.

---

## GET `/api/contracts/{contract_id}`

Contract details. Drives the **Overview** tab and the page header.

Query: `version_id` (optional, default latest).

Response `200`:

```json
{
  "id": "ctr_acme",
  "name": "Acme Services Agreement",
  "version": {
    "id": "ver_acme_1",
    "version_number": 1,
    "file_name": "acme-services-agreement.pdf",
    "uploaded_at": "2026-09-28T09:00:00Z",
    "analysis_status": "completed",
    "is_latest": true
  },
  "version_count": 1,
  "parties": [
    { "item_id": "itm_acme_party_1", "name": "Acme Corporation", "role": "customer",
      "confidence": "high", "review_status": "pending" },
    { "item_id": "itm_acme_party_2", "name": "Example Services Ltd.", "role": "service provider",
      "confidence": "high", "review_status": "pending" }
  ],
  "renewal": { /* Renewal object, see renewals.md (without contract_id/contract_name) */ },
  "counts": {
    "extracted_items": 6,
    "obligations": 3,
    "pending_reviews": 8,
    "open_clarifications": 0
  },
  "lifecycle_status": "expiring_soon",
  "created_at": "2026-09-28T09:00:00Z",
  "updated_at": "2026-09-29T14:10:00Z"
}
```

Before analysis completes, `parties` is `[]` and `renewal` is `null`.

Errors: `CONTRACT_NOT_FOUND`, `VERSION_NOT_FOUND`.

---

## GET `/api/contracts/{contract_id}/extracted-items`

Drives the **Extracted Information** tab.

Query: `version_id` (optional, default latest), `field_name` (optional).

Response `200`:

```json
{
  "items": [
    {
      "id": "itm_acme_notice",
      "contract_version_id": "ver_acme_1",
      "field_name": "notice_period",
      "label": "Notice period",
      "value": { "value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal" },
      "original_value": { "value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal" },
      "display_value": "90 days before expiration (non-renewal)",
      "original_display_value": "90 days before expiration (non-renewal)",
      "confidence": "high",
      "review_status": "pending",
      "ambiguity_note": null,
      "origin": "ai",
      "in_open_clarification": false,
      "clarification_id": null,
      "citations": [ /* Citation objects */ ],
      "updated_at": "2026-09-28T09:02:40Z"
    }
  ]
}
```

`value` shape per `field_name` (the same shape is used when editing via `POST /api/reviews`):

| field_name | value |
|---|---|
| `party` | `{"name": str, "role": str \| null}`. Multiple items allowed. |
| `effective_date` | `{"date": "YYYY-MM-DD", "date_text": str}` |
| `expiration_date` | `{"date": "YYYY-MM-DD", "date_text": str}` |
| `initial_term` | `{"value": int, "unit": "days" \| "months" \| "years"}`, used when the contract states a term length instead of an end date |
| `renewal_terms` | `{"type": "automatic" \| "optional" \| "none", "period_value": int \| null, "period_unit": "days" \| "months" \| "years" \| null}` |
| `notice_period` | `{"value": int, "unit": "days" \| "business_days" \| "months", "anchor": "expiration_date" \| "renewal_date" \| "other", "purpose": "non_renewal" \| "termination" \| "other"}` |
| `termination_clause` | `{"summary": str}`. Informational text only; no date is calculated from it. |

A field with **no item** means it was not found in the document. The UI shows "Not found"
rather than a guess.

Two or more non-rejected items for a single-valued field (anything except `party` and
`termination_clause`) is a conflict. Those items have `in_open_clarification: true`.
