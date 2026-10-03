"""Version listing and comparison with the previous version. Rules: docs/api/versions.md."""

from __future__ import annotations

import re
import sqlite3

from rapidfuzz import fuzz

from backend.core.exceptions import AppError
from backend.services.common import (
    SINGLE_VALUED_FIELDS,
    get_contract,
    get_version,
    latest_version,
    loads,
    new_id,
    utc_now,
)


def serialize_version(conn: sqlite3.Connection, row: sqlite3.Row, latest_id: str | None) -> dict:
    change_count = None
    if row["version_number"] > 1 and row["analysis_status"] == "completed":
        change_count = conn.execute(
            "SELECT COUNT(*) FROM version_changes WHERE contract_version_id = ?", (row["id"],)
        ).fetchone()[0]
    return {
        "id": row["id"],
        "contract_id": row["contract_id"],
        "version_number": row["version_number"],
        "file_name": row["file_name"],
        "mime_type": row["mime_type"],
        "page_count": row["page_count"],
        "uploaded_at": row["uploaded_at"],
        "analysis_status": row["analysis_status"],
        "analysis_completed_at": row["analysis_completed_at"],
        "is_latest": row["id"] == latest_id,
        "change_count": change_count,
    }


def list_versions(conn: sqlite3.Connection, contract_id: str) -> list[dict]:
    get_contract(conn, contract_id)
    latest = latest_version(conn, contract_id)
    rows = conn.execute(
        "SELECT * FROM contract_versions WHERE contract_id = ? ORDER BY version_number DESC", (contract_id,)
    ).fetchall()
    return [serialize_version(conn, r, latest["id"] if latest else None) for r in rows]


def get_version_out(conn: sqlite3.Connection, contract_id: str, version_id: str) -> dict:
    row = get_version(conn, contract_id, version_id)
    latest = latest_version(conn, contract_id)
    return serialize_version(conn, row, latest["id"])


def _previous(conn: sqlite3.Connection, version: sqlite3.Row) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM contract_versions WHERE contract_id = ? AND version_number = ?",
        (version["contract_id"], version["version_number"] - 1),
    ).fetchone()


def changes(conn: sqlite3.Connection, contract_id: str, version_id: str) -> dict:
    version = get_version(conn, contract_id, version_id)
    if version["analysis_status"] != "completed":
        raise AppError("ANALYSIS_NOT_COMPLETE", "This version has not been analyzed yet.", 409)
    previous = _previous(conn, version)
    rows = conn.execute(
        """SELECT c.*, COALESCE(i.review_status, o.review_status) AS previous_review_status
           FROM version_changes c
           LEFT JOIN extracted_items i ON c.entity_type = 'extracted_item' AND i.id = c.previous_entity_id
           LEFT JOIN obligations o ON c.entity_type = 'obligation' AND o.id = c.previous_entity_id
           WHERE c.contract_version_id = ? ORDER BY c.entity_type DESC, c.field_name""",
        (version_id,),
    ).fetchall()
    return {
        "version_id": version_id,
        "previous_version_id": previous["id"] if previous else None,
        "items": [
            {
                "id": r["id"],
                "entity_type": r["entity_type"],
                "field_name": r["field_name"],
                "change_type": r["change_type"],
                "previous_entity_id": r["previous_entity_id"],
                "new_entity_id": r["new_entity_id"],
                "previous_display": r["previous_display"],
                "new_display": r["new_display"],
                "previous_review_status": r["previous_review_status"],
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------- comparison (run at end of analysis)


def _party_key(value: dict) -> str:
    name = re.sub(r"[^a-z0-9 ]", "", (value.get("name") or "").lower())
    return re.sub(r"\s+(inc|ltd|llc|corp|corporation|limited)$", "", name.strip())


def compare_with_previous(conn: sqlite3.Connection, version_id: str) -> int:
    """Write version_changes for version_id vs. its predecessor. Caller commits. Returns change count."""
    version = conn.execute("SELECT * FROM contract_versions WHERE id = ?", (version_id,)).fetchone()
    previous = _previous(conn, version)
    conn.execute("DELETE FROM version_changes WHERE contract_version_id = ?", (version_id,))
    if not previous or previous["analysis_status"] != "completed":
        return 0

    def items(vid: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM extracted_items WHERE contract_version_id = ? AND review_status != 'rejected'", (vid,)
        ).fetchall()

    def obligations(vid: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM obligations WHERE contract_version_id = ? AND review_status != 'rejected'", (vid,)
        ).fetchall()

    found: list[tuple] = []  # (entity_type, field_name, change_type, prev_row, new_row)
    old_items, new_items = items(previous["id"]), items(version_id)

    for field_name in (*SINGLE_VALUED_FIELDS, "termination_clause"):
        old = [r for r in old_items if r["field_name"] == field_name]
        new = [r for r in new_items if r["field_name"] == field_name]
        old_values = sorted(r["display_value"] for r in old)
        new_values = sorted(r["display_value"] for r in new)
        if old_values == new_values:
            continue
        if old and new:
            found.append(("extracted_item", field_name, "modified", old[0], new[0]))
        elif new:
            found.append(("extracted_item", field_name, "added", None, new[0]))
        else:
            found.append(("extracted_item", field_name, "removed", old[0], None))

    old_parties = {_party_key(loads(r["value_json"])): r for r in old_items if r["field_name"] == "party"}
    new_parties = {_party_key(loads(r["value_json"])): r for r in new_items if r["field_name"] == "party"}
    for key in new_parties.keys() - old_parties.keys():
        found.append(("extracted_item", "party", "added", None, new_parties[key]))
    for key in old_parties.keys() - new_parties.keys():
        found.append(("extracted_item", "party", "removed", old_parties[key], None))

    old_obls, new_obls = obligations(previous["id"]), obligations(version_id)
    matched_old: set[str] = set()
    for n in new_obls:
        best, score = None, 0.0
        for o in old_obls:
            if o["id"] in matched_old:
                continue
            s = fuzz.token_set_ratio(o["description"].lower(), n["description"].lower())
            if s > score:
                best, score = o, s
        if best is not None and score >= 80:
            matched_old.add(best["id"])
            before = (best["description"], best["responsible_party"], best["frequency"], best["frequency_text"])
            after = (n["description"], n["responsible_party"], n["frequency"], n["frequency_text"])
            if before != after:
                found.append(("obligation", "obligation", "modified", best, n))
        else:
            found.append(("obligation", "obligation", "added", None, n))
    for o in old_obls:
        if o["id"] not in matched_old:
            found.append(("obligation", "obligation", "removed", o, None))

    def display(entity_type: str, row: sqlite3.Row | None) -> str | None:
        if row is None:
            return None
        return row["display_value"] if entity_type == "extracted_item" else row["description"]

    now = utc_now()
    for entity_type, field_name, change_type, prev_row, new_row in found:
        conn.execute(
            """INSERT INTO version_changes (id, contract_version_id, previous_version_id, entity_type, field_name,
                   change_type, previous_entity_id, new_entity_id, previous_display, new_display, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_id("chg"),
                version_id,
                previous["id"],
                entity_type,
                field_name,
                change_type,
                prev_row["id"] if prev_row else None,
                new_row["id"] if new_row else None,
                display(entity_type, prev_row),
                display(entity_type, new_row),
                now,
            ),
        )
    return len(found)
