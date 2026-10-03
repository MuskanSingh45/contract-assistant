"""Obligations and renewals across contracts. Docs: docs/api/obligations.md, renewals.md."""

from __future__ import annotations

import sqlite3
from datetime import date

from backend.core.exceptions import AppError, not_found
from backend.services import calculation_service
from backend.services.common import (
    citations_for,
    get_version,
    latest_version_ids,
    open_clarification_items,
    placeholders,
    serialize_obligation,
    to_date,
    today,
)
from backend.utils import dates


def list_obligations(
    conn: sqlite3.Connection,
    *,
    contract_id: str | None,
    version_id: str | None,
    status: str | None,
    review_status: str | None,
    responsible_party: str | None,
    due_before: date | None,
) -> list[dict]:
    if version_id:
        if not contract_id:
            raise AppError("VALIDATION_ERROR", "version_id requires contract_id", 422)
        version_ids = [get_version(conn, contract_id, version_id)["id"]]
    else:
        version_ids = latest_version_ids(conn)
    sql = f"""SELECT o.*, v.contract_id FROM obligations o JOIN contract_versions v ON v.id = o.contract_version_id
              WHERE o.contract_version_id IN ({placeholders(version_ids)})"""
    params: list = list(version_ids)
    if contract_id:
        sql += " AND v.contract_id = ?"
        params.append(contract_id)
    if status:
        sql += " AND o.status = ?"
        params.append(status)
    if review_status:
        sql += " AND o.review_status = ?"
        params.append(review_status)
    else:
        sql += " AND o.review_status != 'rejected'"
    if responsible_party:
        sql += " AND LOWER(COALESCE(o.responsible_party, '')) LIKE ?"
        params.append(f"%{responsible_party.lower()}%")
    if due_before:
        sql += " AND o.due_date IS NOT NULL AND o.due_date <= ?"
        params.append(due_before.isoformat())
    rows = conn.execute(sql + " ORDER BY o.due_date IS NULL, o.due_date, o.created_at", params).fetchall()
    contracts = {r["id"]: r for r in conn.execute("SELECT * FROM contracts")}
    cites = citations_for(conn, "obligation", [r["id"] for r in rows])
    open_items = open_clarification_items(conn, version_ids)
    ref = today()
    return [
        serialize_obligation(r, contracts[r["contract_id"]], cites[r["id"]], ref, open_items.get(r["id"])) for r in rows
    ]


def get_obligation(conn: sqlite3.Connection, obligation_id: str) -> dict:
    row = conn.execute(
        """SELECT o.*, v.contract_id FROM obligations o JOIN contract_versions v ON v.id = o.contract_version_id
           WHERE o.id = ?""",
        (obligation_id,),
    ).fetchone()
    if not row:
        raise not_found("OBLIGATION_NOT_FOUND", "Obligation")
    contract = conn.execute("SELECT * FROM contracts WHERE id = ?", (row["contract_id"],)).fetchone()
    cites = citations_for(conn, "obligation", [obligation_id])[obligation_id]
    clq = open_clarification_items(conn, [row["contract_version_id"]]).get(obligation_id)
    return serialize_obligation(row, contract, cites, today(), clq)


def list_renewals(conn: sqlite3.Connection, within_days: int | None, calculation_status: str | None) -> list[dict]:
    ref = today()
    out = []
    for vid in latest_version_ids(conn):
        contract = conn.execute(
            "SELECT c.* FROM contracts c JOIN contract_versions v ON v.contract_id = c.id WHERE v.id = ?", (vid,)
        ).fetchone()
        renewal = calculation_service.serialize_renewal(conn, vid, contract, ref)
        if not renewal:
            continue
        if calculation_status and renewal["calculation_status"] != calculation_status:
            continue
        if within_days is not None:
            key = to_date(renewal["notice_deadline"] or renewal["current_term_end"])
            days = dates.days_until(key, ref)
            if days is None or not 0 <= days <= within_days:
                continue
        out.append(renewal)
    out.sort(key=lambda r: (r["notice_deadline"] is None, r["notice_deadline"] or ""))
    return out
