# Versions API

Each uploaded document is a version. Versions are never overwritten. A new version is
analyzed independently and then compared with the version before it.

## Version object

```json
{
  "id": "ver_acme_2",
  "contract_id": "ctr_acme",
  "version_number": 2,
  "file_name": "acme-v2.pdf",
  "mime_type": "application/pdf",
  "page_count": 15,
  "uploaded_at": "2026-10-03T10:00:00Z",
  "analysis_status": "completed",
  "analysis_completed_at": "2026-10-03T10:03:10Z",
  "is_latest": true,
  "change_count": 2
}
```

`change_count` is `null` for version 1 and while the version is not yet analyzed.

## GET `/api/contracts/{contract_id}/versions`

Response `200`: `{"items": [Version, ...]}`, newest first.

## POST `/api/contracts/{contract_id}/versions`

Same `multipart/form-data` as `POST /api/contracts` (`file` required, no `name`). Creates
version N+1 with `analysis_status: "not_started"`. Earlier versions and their reviewed data
are untouched. The frontend then calls `POST /api/contracts/{id}/analyze`.

Response `201`: Version object.
Errors: as for upload, plus `CONTRACT_NOT_FOUND`. If the file hash equals the latest
version's hash, the result is `DUPLICATE_VERSION` (409).

## GET `/api/contracts/{contract_id}/versions/{version_id}/changes`

Comparison of this version with the previous version (`version_number - 1`). It is computed
at the end of analysis (stage `analyzing`) and stored in `version_changes`.

Response `200`:

```json
{
  "version_id": "ver_acme_2",
  "previous_version_id": "ver_acme_1",
  "items": [
    {
      "id": "chg_1",
      "entity_type": "extracted_item",
      "field_name": "notice_period",
      "change_type": "modified",
      "previous_entity_id": "itm_acme_notice",
      "new_entity_id": "itm_acme2_notice",
      "previous_display": "90 days before expiration (non-renewal)",
      "new_display": "60 days before expiration (non-renewal)",
      "previous_review_status": "approved"
    },
    {
      "id": "chg_2",
      "entity_type": "obligation",
      "field_name": "obligation",
      "change_type": "added",
      "previous_entity_id": null,
      "new_entity_id": "obl_acme2_security",
      "previous_display": null,
      "new_display": "Submit monthly security report",
      "previous_review_status": null
    }
  ]
}
```

- `change_type`: `added`, `removed`, `modified`. Unchanged items are not listed.
- **Potentially stale** means a previous-version item referenced by a `modified` or `removed` change. It is shown in the Versions tab, and most visibly when that item had already been approved (`previous_review_status`). Nothing in the old version is deleted or changed.
- Matching rules (deterministic, no LLM): extracted items match by `field_name` (parties by normalized name). Obligations match by normalized description similarity of 0.8 or more (rapidfuzz `token_set_ratio`), otherwise they count as added/removed.
- Version 1 returns `previous_version_id: null` and `items: []`.

Errors: `CONTRACT_NOT_FOUND`, `VERSION_NOT_FOUND`, `ANALYSIS_NOT_COMPLETE` (409).
