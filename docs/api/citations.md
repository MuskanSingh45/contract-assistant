# Citations API

Citations are embedded in extracted items, obligations, review queue items and
clarifications (see the Citation object in [api-contract.md](api-contract.md)). This
endpoint supplies the extra context for the **source drawer**. The MVP uses a drawer, not
a PDF viewer.

## GET `/api/citations/{citation_id}`

Response `200`:

```json
{
  "id": "cit_acme_notice",
  "contract_id": "ctr_acme",
  "contract_version_id": "ver_acme_1",
  "version_number": 1,
  "file_name": "acme-services-agreement.pdf",
  "entity_type": "extracted_item",
  "entity_id": "itm_acme_notice",
  "page": 2,
  "section": "2.2 Renewal",
  "source_text": "at least ninety (90) days before the expiration of the then-current term",
  "validation_status": "verified",
  "segment": {
    "text": "This Agreement shall automatically renew for successive twelve (12) month periods unless either party provides written notice of non-renewal at least ninety (90) days before the expiration of the then-current term.",
    "highlight": { "start": 141, "end": 213 }
  },
  "context_before": "The initial term of this Agreement shall commence on the Effective Date and expire on January 31, 2027.",
  "context_after": null
}
```

- `segment.text` is the parsed segment that contains the quote. `highlight` gives character offsets of the quote within `segment.text`. It is `null` when `validation_status` is `not_found`.
- `context_before` / `context_after` are the neighbouring segments' text, or `null`.
- When `validation_status = "not_found"`, the drawer must show a warning: "The quoted text could not be found in the document. Verify this item manually."

Error: `CITATION_NOT_FOUND`.
