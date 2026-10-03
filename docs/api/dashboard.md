# Dashboard API

## GET `/api/dashboard`

One request for the whole Dashboard page. Latest versions only.

Response `200`:

```json
{
  "counts": {
    "contracts": 2,
    "contracts_needing_review": 2,
    "upcoming_notice_deadlines": 1,
    "open_obligations": 3,
    "open_clarifications": 1
  },
  "upcoming_deadlines": [
    {
      "type": "obligation",
      "contract_id": "ctr_acme",
      "contract_name": "Acme Services Agreement",
      "label": "Submit quarterly compliance report",
      "date": "2026-10-30",
      "days_until": 27,
      "entity_id": "obl_acme_report"
    },
    {
      "type": "notice_deadline",
      "contract_id": "ctr_acme",
      "contract_name": "Acme Services Agreement",
      "label": "Non-renewal notice deadline",
      "date": "2026-11-02",
      "days_until": 30,
      "entity_id": null
    }
  ],
  "recent_activity": [
    {
      "type": "review",
      "contract_id": "ctr_acme",
      "contract_name": "Acme Services Agreement",
      "description": "Effective date approved",
      "at": "2026-09-29T14:10:00Z"
    }
  ]
}
```

- "Upcoming" means within `UPCOMING_WINDOW_DAYS` (default 60) from today, sorted by date.
- `upcoming_deadlines` contains notice deadlines and open obligations with a `due_date`, at most 10.
- `recent_activity` types: `upload` (version uploaded), `analysis` (completed/failed), `review` (review action), `clarification` (resolved). At most 10, newest first. It is built from existing timestamps; there is no separate activity table.
