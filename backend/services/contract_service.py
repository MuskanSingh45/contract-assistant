"""Contracts: list, details, extracted items, dashboard. Shapes: docs/api/contracts.md, dashboard.md."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from backend.services import calculation_service
from backend.services.common import (
    FIELD_LABELS,
    citations_for,
    get_contract,
    get_version,
    latest_version,
    latest_version_ids,
    loads,
    open_clarification_items,
    placeholders,
    serialize_item,
    to_date,
    today,
    version_counts,
)
from backend.utils import dates


def _version_brief(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    return {"id": row["id"], "version_number": row["version_number"], "analysis_status": row["analysis_status"]}


def _parties(conn: sqlite3.Connection, version_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM extracted_items WHERE contract_version_id = ? AND field_name = 'party'
           AND review_status != 'rejected' ORDER BY created_at, id""",
        (version_id,),
    ).fetchall()


def contract_summary(conn: sqlite3.Connection, contract: sqlite3.Row, ref: date | None = None) -> dict:
    ref = ref or today()
    version = latest_version(conn, contract["id"])
    renewal = calculation_service.serialize_renewal(conn, version["id"], contract, ref) if version else None
    counts = version_counts(conn, version["id"]) if version else {"pending_reviews": 0, "open_clarifications": 0}
    return {
        "id": contract["id"],
        "name": contract["name"],
        "parties": [loads(p["value_json"])["name"] for p in _parties(conn, version["id"])] if version else [],
        "effective_date": renewal["effective_date"] if renewal else None,
        "expiration_date": renewal["expiration_date"] if renewal else None,
        "current_term_end": renewal["current_term_end"] if renewal else None,
        "renewal_type": renewal["renewal_type"] if renewal else None,
        "notice_deadline": renewal["notice_deadline"] if renewal else None,
        "days_until_notice_deadline": renewal["days_until_notice_deadline"] if renewal else None,
        "lifecycle_status": renewal["lifecycle_status"] if renewal else "unknown",
        "latest_version": _version_brief(version),
        "pending_review_count": counts["pending_reviews"],
        "open_clarification_count": counts["open_clarifications"],
        "created_at": contract["created_at"],
        "updated_at": contract["updated_at"],
    }


def list_contracts(
    conn: sqlite3.Connection, search: str | None, lifecycle_status: str | None, needs_review: bool | None
) -> list[dict]:
    rows = conn.execute("SELECT * FROM contracts ORDER BY updated_at DESC").fetchall()
    items = [contract_summary(conn, row) for row in rows]
    if search:
        needle = search.lower()
        items = [c for c in items if needle in c["name"].lower() or any(needle in p.lower() for p in c["parties"])]
    if lifecycle_status:
        items = [c for c in items if c["lifecycle_status"] == lifecycle_status]
    if needs_review:
        items = [c for c in items if c["pending_review_count"] > 0 or c["open_clarification_count"] > 0]
    return items


def contract_detail(conn: sqlite3.Connection, contract_id: str, version_id: str | None) -> dict:
    contract = get_contract(conn, contract_id)
    version = get_version(conn, contract_id, version_id)
    latest = latest_version(conn, contract_id)
    renewal = calculation_service.serialize_renewal(conn, version["id"], contract)
    version_count = conn.execute(
        "SELECT COUNT(*) FROM contract_versions WHERE contract_id = ?", (contract_id,)
    ).fetchone()[0]
    parties = [
        {
            "item_id": p["id"],
            **{k: loads(p["value_json"]).get(k) for k in ("name", "role")},
            "confidence": p["confidence"],
            "review_status": p["review_status"],
        }
        for p in _parties(conn, version["id"])
    ]
    return {
        "id": contract["id"],
        "name": contract["name"],
        "version": {
            "id": version["id"],
            "version_number": version["version_number"],
            "file_name": version["file_name"],
            "uploaded_at": version["uploaded_at"],
            "analysis_status": version["analysis_status"],
            "is_latest": version["id"] == latest["id"],
        },
        "version_count": version_count,
        "parties": parties,
        "renewal": renewal,
        "counts": version_counts(conn, version["id"]),
        "lifecycle_status": renewal["lifecycle_status"] if renewal else "unknown",
        "created_at": contract["created_at"],
        "updated_at": contract["updated_at"],
    }


def extracted_items(
    conn: sqlite3.Connection, contract_id: str, version_id: str | None, field_name: str | None
) -> list[dict]:
    version = get_version(conn, contract_id, version_id)
    sql = "SELECT * FROM extracted_items WHERE contract_version_id = ?"
    params: list = [version["id"]]
    if field_name:
        sql += " AND field_name = ?"
        params.append(field_name)
    order = {f: i for i, f in enumerate(FIELD_LABELS)}
    rows = sorted(
        conn.execute(sql + " ORDER BY created_at, id", params).fetchall(),
        key=lambda r: order.get(r["field_name"], len(order)),
    )
    cites = citations_for(conn, "extracted_item", [r["id"] for r in rows])
    open_items = open_clarification_items(conn, [version["id"]])
    return [serialize_item(r, cites[r["id"]], open_items.get(r["id"])) for r in rows]


# ---------------------------------------------------------------- dashboard


def dashboard(conn: sqlite3.Connection) -> dict:
    from backend.core.config import settings

    ref = today()
    horizon = ref + timedelta(days=settings.upcoming_window_days)
    contracts = {r["id"]: r for r in conn.execute("SELECT * FROM contracts").fetchall()}
    summaries = [contract_summary(conn, c, ref) for c in contracts.values()]
    version_ids = latest_version_ids(conn)
    ph = placeholders(version_ids)

    deadlines = []
    for s in summaries:
        d = to_date(s["notice_deadline"])
        if d and ref <= d <= horizon:
            deadlines.append(
                {
                    "type": "notice_deadline",
                    "contract_id": s["id"],
                    "contract_name": s["name"],
                    "label": "Non-renewal notice deadline",
                    "date": s["notice_deadline"],
                    "days_until": dates.days_until(d, ref),
                    "entity_id": None,
                }
            )
    obligation_rows = conn.execute(
        f"""SELECT o.*, v.contract_id FROM obligations o JOIN contract_versions v ON v.id = o.contract_version_id
            WHERE o.contract_version_id IN ({ph}) AND o.status = 'open' AND o.review_status != 'rejected'""",
        version_ids,
    ).fetchall()
    for o in obligation_rows:
        d = to_date(o["due_date"])
        if d and ref <= d <= horizon:
            deadlines.append(
                {
                    "type": "obligation",
                    "contract_id": o["contract_id"],
                    "contract_name": contracts[o["contract_id"]]["name"],
                    "label": o["description"],
                    "date": o["due_date"],
                    "days_until": dates.days_until(d, ref),
                    "entity_id": o["id"],
                }
            )
    deadlines.sort(key=lambda x: x["date"])

    open_clarifications = conn.execute(
        f"SELECT COUNT(*) FROM clarification_questions WHERE status = 'open' AND contract_version_id IN ({ph})",
        version_ids,
    ).fetchone()[0]
    return {
        "counts": {
            "contracts": len(summaries),
            "contracts_needing_review": sum(
                1 for s in summaries if s["pending_review_count"] or s["open_clarification_count"]
            ),
            "upcoming_notice_deadlines": sum(1 for d in deadlines if d["type"] == "notice_deadline"),
            "open_obligations": len(obligation_rows),
            "open_clarifications": open_clarifications,
        },
        "upcoming_deadlines": deadlines[:10],
        "recent_activity": _recent_activity(conn, contracts),
    }


def _recent_activity(conn: sqlite3.Connection, contracts: dict) -> list[dict]:
    events = []
    for v in conn.execute("SELECT * FROM contract_versions").fetchall():
        name = contracts[v["contract_id"]]["name"]
        events.append(
            {
                "type": "upload",
                "contract_id": v["contract_id"],
                "contract_name": name,
                "description": f"Version {v['version_number']} uploaded ({v['file_name']})",
                "at": v["uploaded_at"],
            }
        )
        if v["analysis_status"] in ("completed", "failed") and v["analysis_completed_at"]:
            events.append(
                {
                    "type": "analysis",
                    "contract_id": v["contract_id"],
                    "contract_name": name,
                    "description": f"Analysis {v['analysis_status']} for version {v['version_number']}",
                    "at": v["analysis_completed_at"],
                }
            )
    review_rows = conn.execute(
        """SELECT r.*, v.contract_id, COALESCE(i.field_name, 'obligation') AS field_name
           FROM reviews r
           LEFT JOIN extracted_items i ON r.entity_type = 'extracted_item' AND i.id = r.entity_id
           LEFT JOIN obligations o ON r.entity_type = 'obligation' AND o.id = r.entity_id
           JOIN contract_versions v ON v.id = COALESCE(i.contract_version_id, o.contract_version_id)
           ORDER BY r.reviewed_at DESC LIMIT 10"""
    ).fetchall()
    verbs = {"approve": "approved", "edit": "edited", "reject": "rejected"}
    for r in review_rows:
        label = FIELD_LABELS.get(r["field_name"], "Obligation")
        events.append(
            {
                "type": "review",
                "contract_id": r["contract_id"],
                "contract_name": contracts[r["contract_id"]]["name"],
                "description": f"{label} {verbs[r['action']]}",
                "at": r["reviewed_at"],
            }
        )
    for q in conn.execute(
        """SELECT q.*, v.contract_id FROM clarification_questions q
           JOIN contract_versions v ON v.id = q.contract_version_id WHERE q.resolved_at IS NOT NULL"""
    ).fetchall():
        events.append(
            {
                "type": "clarification",
                "contract_id": q["contract_id"],
                "contract_name": contracts[q["contract_id"]]["name"],
                "description": f"Clarification {q['status']}: "
                + FIELD_LABELS.get(q["field_name"] or "", "contract term"),
                "at": q["resolved_at"],
            }
        )
    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:10]
