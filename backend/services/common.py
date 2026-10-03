"""Helpers shared by services: ids, time, lookups and serialization to the documented API shapes."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, date, datetime
from typing import Any

from backend.core.exceptions import AppError, not_found

DATE_INPUT_FIELDS = ("effective_date", "expiration_date", "initial_term", "renewal_terms", "notice_period")
SINGLE_VALUED_FIELDS = DATE_INPUT_FIELDS

FIELD_LABELS = {
    "party": "Party",
    "effective_date": "Effective date",
    "expiration_date": "Expiration date",
    "initial_term": "Initial term",
    "renewal_terms": "Renewal terms",
    "notice_period": "Notice period",
    "termination_clause": "Termination clause",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> date:
    # Deadlines are calendar days for the person using the app, so "today" is the local date.
    return date.today()  # noqa: DTZ011


def loads(value: str | None) -> Any:
    return json.loads(value) if value else None


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def to_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


# ---------------------------------------------------------------- lookups


def get_contract(conn: sqlite3.Connection, contract_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    if not row:
        raise not_found("CONTRACT_NOT_FOUND", "Contract")
    return row


def latest_version(conn: sqlite3.Connection, contract_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM contract_versions WHERE contract_id = ? ORDER BY version_number DESC LIMIT 1",
        (contract_id,),
    ).fetchone()


def get_version(conn: sqlite3.Connection, contract_id: str, version_id: str | None) -> sqlite3.Row:
    """The given version of a contract, or its latest version when version_id is None."""
    get_contract(conn, contract_id)
    if version_id is None:
        row = latest_version(conn, contract_id)
    else:
        row = conn.execute(
            "SELECT * FROM contract_versions WHERE id = ? AND contract_id = ?",
            (version_id, contract_id),
        ).fetchone()
    if not row:
        raise not_found("VERSION_NOT_FOUND", "Version")
    return row


def latest_version_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """SELECT v.id FROM contract_versions v
           WHERE v.version_number = (SELECT MAX(version_number) FROM contract_versions
                                     WHERE contract_id = v.contract_id)"""
    ).fetchall()
    return [r["id"] for r in rows]


def placeholders(values: list[Any]) -> str:
    return ",".join("?" for _ in values) or "NULL"


def require(condition: bool, code: str, message: str, status: int = 400, details: Any = None):
    if not condition:
        raise AppError(code, message, status, details)


# ---------------------------------------------------------------- citations


def serialize_citation(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "contract_version_id": row["contract_version_id"],
        "page": row["page"],
        "section": row["section"],
        "source_text": row["source_text"],
        "validation_status": row["validation_status"],
    }


def citations_for(conn: sqlite3.Connection, entity_type: str, ids: list[str]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {i: [] for i in ids}
    if not ids:
        return result
    rows = conn.execute(
        f"""SELECT c.* FROM citations c LEFT JOIN document_segments s ON s.id = c.segment_id
            WHERE c.entity_type = ? AND c.entity_id IN ({placeholders(ids)})
            ORDER BY s.seq, c.char_start""",
        (entity_type, *ids),
    ).fetchall()
    for row in rows:
        result[row["entity_id"]].append(serialize_citation(row))
    return result


# ---------------------------------------------------------------- items


def open_clarification_items(conn: sqlite3.Connection, version_ids: list[str]) -> dict[str, str]:
    """entity_id -> clarification_id for options of open clarifications."""
    if not version_ids:
        return {}
    rows = conn.execute(
        f"""SELECT o.entity_id, q.id FROM clarification_options o
            JOIN clarification_questions q ON q.id = o.clarification_id
            WHERE q.status = 'open' AND q.contract_version_id IN ({placeholders(version_ids)})""",
        version_ids,
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _display(field_name: str, value: dict) -> str:
    from ai.pipeline.clarification import display_value

    return display_value(field_name, value)


def serialize_item(row: sqlite3.Row, citations: list[dict], clarification_id: str | None) -> dict:
    return {
        "id": row["id"],
        "contract_version_id": row["contract_version_id"],
        "field_name": row["field_name"],
        "label": FIELD_LABELS.get(row["field_name"], row["field_name"]),
        "value": loads(row["value_json"]),
        "original_value": loads(row["original_value_json"]),
        "display_value": row["display_value"],
        "original_display_value": _display(row["field_name"], loads(row["original_value_json"])),
        "confidence": row["confidence"],
        "review_status": row["review_status"],
        "ambiguity_note": row["ambiguity_note"],
        "origin": row["origin"],
        "in_open_clarification": clarification_id is not None,
        "clarification_id": clarification_id,
        "citations": citations,
        "updated_at": row["updated_at"],
    }


def obligation_fields(row: sqlite3.Row) -> dict:
    return {
        "description": row["description"],
        "responsible_party": row["responsible_party"],
        "frequency": row["frequency"],
        "frequency_text": row["frequency_text"],
        "due_rule": loads(row["due_rule_json"]),
        "due_date": row["due_date"],
    }


def serialize_obligation(
    row: sqlite3.Row, contract: sqlite3.Row, citations: list[dict], ref: date, clarification_id: str | None = None
) -> dict:
    due = to_date(row["due_date"])
    return {
        "id": row["id"],
        "contract_id": contract["id"],
        "contract_name": contract["name"],
        "contract_version_id": row["contract_version_id"],
        **obligation_fields(row),
        "due_date_source": row["due_date_source"],
        "days_until_due": (due - ref).days if due else None,
        "status": row["status"],
        "confidence": row["confidence"],
        "review_status": row["review_status"],
        "original_value": loads(row["original_value_json"]),
        "ambiguity_note": row["ambiguity_note"],
        "in_open_clarification": clarification_id is not None,
        "citations": citations,
        "updated_at": row["updated_at"],
    }


def version_counts(conn: sqlite3.Connection, version_id: str) -> dict[str, int]:
    """Review workload of one version, shared by the contract detail and the analysis summary."""

    def one(sql: str) -> int:
        return conn.execute(sql, (version_id,)).fetchone()[0]

    pending = "SELECT COUNT(*) FROM {} WHERE contract_version_id = ?1 AND review_status = 'pending'"
    return {
        "extracted_items": one("SELECT COUNT(*) FROM extracted_items WHERE contract_version_id = ?"),
        "obligations": one("SELECT COUNT(*) FROM obligations WHERE contract_version_id = ?"),
        "pending_reviews": one(f"SELECT ({pending.format('extracted_items')}) + ({pending.format('obligations')})"),
        "open_clarifications": one(
            "SELECT COUNT(*) FROM clarification_questions WHERE contract_version_id = ? AND status = 'open'"
        ),
    }
