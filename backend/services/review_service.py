"""Review queue, approve/edit/reject, history, clarifications, citations.

Docs: docs/api/reviews.md, clarifications.md, citations.md, docs/decisions/006-review-and-calculation-model.md.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema

from ai.pipeline import clarification as templates
from backend.core.exceptions import AppError, not_found
from backend.services import calculation_service
from backend.services.common import (
    DATE_INPUT_FIELDS,
    FIELD_LABELS,
    citations_for,
    dumps,
    latest_version_ids,
    loads,
    new_id,
    obligation_fields,
    open_clarification_items,
    placeholders,
    serialize_item,
    serialize_obligation,
    today,
    utc_now,
)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "ai" / "schemas"
ACTION_STATUS = {"approve": "approved", "edit": "edited", "reject": "rejected"}
OBLIGATION_EDIT_FIELDS = ("description", "responsible_party", "frequency", "frequency_text", "due_rule", "due_date")


# ---------------------------------------------------------------- value validation


@cache
def _value_schemas() -> dict[str, dict]:
    terms = json.loads((SCHEMA_DIR / "extraction.json").read_text())["properties"]
    keys = {"party": "parties"}
    out = {f: terms[keys.get(f, f)]["items"]["properties"]["value"] for f in FIELD_LABELS}
    out["obligation"] = json.loads((SCHEMA_DIR / "obligation.json").read_text())["properties"]["obligations"]["items"][
        "properties"
    ]["value"]
    return out


def _schema_errors(schema: dict, value: Any) -> list[dict]:
    validator = jsonschema.Draft202012Validator(schema)
    return [
        {
            "field": "value." + ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "value",
            "problem": e.message,
        }
        for e in validator.iter_errors(value)
    ]


def _check_date(value: Any, path: str) -> list[dict]:
    if value is None:
        return []
    try:
        date.fromisoformat(value)
        return []
    except (TypeError, ValueError):
        return [{"field": path, "problem": "not a valid date (YYYY-MM-DD)"}]


def validate_item_value(field_name: str, value: Any) -> dict:
    if field_name in ("effective_date", "expiration_date") and isinstance(value, dict):
        value = {**value, "date_text": value.get("date_text") or value.get("date") or ""}
    errors = _schema_errors(_value_schemas()[field_name], value)
    if not errors and field_name in ("effective_date", "expiration_date"):
        errors = _check_date(value.get("date"), "value.date")
        if not value.get("date"):
            errors.append({"field": "value.date", "problem": "a date is required"})
    if errors:
        raise AppError("VALIDATION_ERROR", "Edited value does not match the field's shape.", 422, {"fields": errors})
    return value


def validate_obligation_edit(value: Any) -> dict:
    if not isinstance(value, dict) or not value:
        raise AppError("VALIDATION_ERROR", "Obligation edit must be an object with fields to change.", 422)
    unknown = sorted(set(value) - set(OBLIGATION_EDIT_FIELDS))
    if unknown:
        raise AppError(
            "VALIDATION_ERROR",
            f"Fields cannot be edited: {', '.join(unknown)}",
            422,
            {"fields": [{"field": f"value.{f}", "problem": "not editable"} for f in unknown]},
        )
    props = _value_schemas()["obligation"]["properties"]
    errors = []
    for key, v in value.items():
        if key == "due_date":
            errors += _check_date(v, "value.due_date")
        else:
            errors += [{**e, "field": f"value.{key}"} for e in _schema_errors(props[key], v)]
    if errors:
        raise AppError("VALIDATION_ERROR", "Edited value is invalid.", 422, {"fields": errors})
    return value


# ---------------------------------------------------------------- lookups


def _get_entity(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> sqlite3.Row:
    table = {"extracted_item": "extracted_items", "obligation": "obligations"}.get(entity_type)
    if not table:
        raise AppError("VALIDATION_ERROR", "entity_type must be extracted_item or obligation", 422)
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()
    if not row:
        raise not_found("ITEM_NOT_FOUND", "Item")
    return row


def _contract_for_version(conn: sqlite3.Connection, version_id: str) -> sqlite3.Row:
    return conn.execute(
        "SELECT c.* FROM contracts c JOIN contract_versions v ON v.contract_id = c.id WHERE v.id = ?",
        (version_id,),
    ).fetchone()


def serialize_entity(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> dict:
    row = _get_entity(conn, entity_type, entity_id)
    open_items = open_clarification_items(conn, [row["contract_version_id"]])
    cites = citations_for(conn, entity_type, [entity_id])[entity_id]
    if entity_type == "extracted_item":
        return serialize_item(row, cites, open_items.get(entity_id))
    contract = _contract_for_version(conn, row["contract_version_id"])
    return serialize_obligation(row, contract, cites, today(), open_items.get(entity_id))


def _serialize_review(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "action": row["action"],
        "previous_review_status": row["previous_review_status"],
        "new_review_status": row["new_review_status"],
        "previous_value": loads(row["previous_value_json"]),
        "new_value": loads(row["new_value_json"]),
        "note": row["note"],
        "clarification_id": row["clarification_id"],
        "reviewed_at": row["reviewed_at"],
    }


# ---------------------------------------------------------------- queue & history


def queue(conn: sqlite3.Connection, contract_id: str | None, entity_type: str | None) -> list[dict]:
    version_ids = latest_version_ids(conn)
    if contract_id:
        version_ids = [
            r["id"]
            for r in conn.execute(
                f"SELECT id FROM contract_versions WHERE contract_id = ? AND id IN ({placeholders(version_ids)})",
                (contract_id, *version_ids),
            )
        ]
    ph = placeholders(version_ids)
    open_items = open_clarification_items(conn, version_ids)
    contracts = {
        r["vid"]: r
        for r in conn.execute(
            "SELECT c.id, c.name, v.id AS vid FROM contracts c"
            f" JOIN contract_versions v ON v.contract_id = c.id WHERE v.id IN ({ph})",
            version_ids,
        )
    }
    out: list[dict] = []
    if entity_type in (None, "extracted_item"):
        rows = conn.execute(
            f"SELECT * FROM extracted_items WHERE review_status = 'pending' AND contract_version_id IN ({ph})",
            version_ids,
        ).fetchall()
        cites = citations_for(conn, "extracted_item", [r["id"] for r in rows])
        for r in rows:
            out.append(
                {
                    "entity_type": "extracted_item",
                    "entity_id": r["id"],
                    "field_name": r["field_name"],
                    "label": FIELD_LABELS.get(r["field_name"], r["field_name"]),
                    "display_value": r["display_value"],
                    "value": loads(r["value_json"]),
                    "confidence": r["confidence"],
                    "review_status": r["review_status"],
                    "ambiguity_note": r["ambiguity_note"],
                    "clarification_id": open_items.get(r["id"]),
                    "citations": cites[r["id"]],
                    "_version": r["contract_version_id"],
                }
            )
    if entity_type in (None, "obligation"):
        rows = conn.execute(
            f"SELECT * FROM obligations WHERE review_status = 'pending' AND contract_version_id IN ({ph})",
            version_ids,
        ).fetchall()
        cites = citations_for(conn, "obligation", [r["id"] for r in rows])
        for r in rows:
            out.append(
                {
                    "entity_type": "obligation",
                    "entity_id": r["id"],
                    "field_name": None,
                    "label": "Obligation",
                    "display_value": r["description"],
                    "value": obligation_fields(r),
                    "confidence": r["confidence"],
                    "review_status": r["review_status"],
                    "ambiguity_note": r["ambiguity_note"],
                    "clarification_id": open_items.get(r["id"]),
                    "citations": cites[r["id"]],
                    "_version": r["contract_version_id"],
                }
            )
    for item in out:
        c = contracts[item.pop("_version")]
        item.update({"contract_id": c["id"], "contract_name": c["name"], "contract_version_id": c["vid"]})

    def priority(item: dict) -> tuple:
        not_found_cite = any(c["validation_status"] == "not_found" for c in item["citations"])
        return (
            0 if item["clarification_id"] else 1,
            {"low": 0, "medium": 1, "high": 2}[item["confidence"]] - (1 if not_found_cite else 0),
            item["contract_name"],
        )

    return sorted(out, key=priority)


def history(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> list[dict]:
    _get_entity(conn, entity_type, entity_id)
    rows = conn.execute(
        "SELECT * FROM reviews WHERE entity_type = ? AND entity_id = ? ORDER BY reviewed_at DESC, rowid DESC",
        (entity_type, entity_id),
    ).fetchall()
    return [_serialize_review(r) for r in rows]


# ---------------------------------------------------------------- review actions


def _record(conn, entity_type, entity_id, action, prev_status, new_status, prev_value, new_value, note, clq_id=None):
    review_id = new_id("rev")
    conn.execute(
        """INSERT INTO reviews (id, entity_type, entity_id, action, previous_review_status, new_review_status,
               previous_value_json, new_value_json, note, clarification_id, reviewed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            review_id,
            entity_type,
            entity_id,
            action,
            prev_status,
            new_status,
            dumps(prev_value) if prev_value is not None else None,
            dumps(new_value) if new_value is not None else None,
            note,
            clq_id,
            utc_now(),
        ),
    )
    return review_id


def _set_status(conn, entity_type: str, entity_id: str, status: str) -> None:
    table = "extracted_items" if entity_type == "extracted_item" else "obligations"
    conn.execute(f"UPDATE {table} SET review_status = ?, updated_at = ? WHERE id = ?", (status, utc_now(), entity_id))


def _touch_contract(conn, version_id: str) -> None:
    conn.execute(
        "UPDATE contracts SET updated_at = ? WHERE id = (SELECT contract_id FROM contract_versions WHERE id = ?)",
        (utc_now(), version_id),
    )


def apply_review(
    conn: sqlite3.Connection, entity_type: str, entity_id: str, action: str, value: Any, note: str | None
) -> dict:
    if action not in ACTION_STATUS:
        raise AppError("INVALID_REVIEW_ACTION", "action must be approve, edit or reject", 400)
    if action == "edit" and value is None:
        raise AppError("INVALID_REVIEW_ACTION", "edit requires a value", 400)
    if action != "edit" and value is not None:
        raise AppError("INVALID_REVIEW_ACTION", f"{action} must not include a value", 400)
    row = _get_entity(conn, entity_type, entity_id)
    version_id = row["contract_version_id"]
    new_status = ACTION_STATUS[action]
    prev_value = new_value = None

    if action == "edit" and entity_type == "extracted_item":
        new_value = validate_item_value(row["field_name"], value)
        prev_value = loads(row["value_json"])
        conn.execute(
            "UPDATE extracted_items SET value_json = ?, display_value = ? WHERE id = ?",
            (dumps(new_value), templates.display_value(row["field_name"], new_value), entity_id),
        )
    elif action == "edit":
        new_value = validate_obligation_edit(value)
        prev_value = obligation_fields(row)
        _apply_obligation_edit(conn, row, new_value)

    _set_status(conn, entity_type, entity_id, new_status)
    review_id = _record(
        conn, entity_type, entity_id, action, row["review_status"], new_status, prev_value, new_value, note
    )
    affects_dates = entity_type == "obligation" or row["field_name"] in DATE_INPUT_FIELDS
    if affects_dates:
        calculation_service.recalculate(conn, version_id)
    _touch_contract(conn, version_id)
    conn.commit()

    contract = _contract_for_version(conn, version_id)
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    return {
        "item": serialize_entity(conn, entity_type, entity_id),
        "review": _serialize_review(review),
        "renewal": calculation_service.serialize_renewal(conn, version_id, contract) if affects_dates else None,
    }


def _apply_obligation_edit(conn, row: sqlite3.Row, edit: dict) -> None:
    rule = loads(row["due_rule_json"]) or {"basis": "unspecified", "offset_days": 0}
    if "due_rule" in edit:
        rule = dict(edit["due_rule"])
    if edit.get("due_date"):
        rule = {"basis": "explicit_date", "offset_days": 0, "due_date_text": edit["due_date"]}
    conn.execute(
        """UPDATE obligations SET description = ?, responsible_party = ?, frequency = ?, frequency_text = ?,
               due_rule_json = ? WHERE id = ?""",
        (
            edit.get("description", row["description"]),
            edit.get("responsible_party", row["responsible_party"]),
            edit.get("frequency", row["frequency"]),
            edit.get("frequency_text", row["frequency_text"]),
            dumps(rule),
            row["id"],
        ),
    )


def set_obligation_status(conn: sqlite3.Connection, obligation_id: str, body: dict) -> dict:
    extra = sorted(set(body) - {"status"})
    if extra or body.get("status") not in ("open", "completed", "not_applicable"):
        raise AppError(
            "VALIDATION_ERROR",
            "Only status (open, completed, not_applicable) can be changed here. Use POST /api/reviews to edit content.",
            422,
            {"fields": [{"field": f, "problem": "not editable"} for f in extra]},
        )
    row = conn.execute("SELECT * FROM obligations WHERE id = ?", (obligation_id,)).fetchone()
    if not row:
        raise not_found("OBLIGATION_NOT_FOUND", "Obligation")
    conn.execute(
        "UPDATE obligations SET status = ?, updated_at = ? WHERE id = ?", (body["status"], utc_now(), obligation_id)
    )
    conn.commit()
    return serialize_entity(conn, "obligation", obligation_id)


# ---------------------------------------------------------------- clarifications


def serialize_clarification(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    contract = _contract_for_version(conn, row["contract_version_id"])
    option_rows = conn.execute(
        "SELECT entity_type, entity_id FROM clarification_options WHERE clarification_id = ?", (row["id"],)
    ).fetchall()
    options = []
    for o in option_rows:
        item = (
            conn.execute("SELECT * FROM extracted_items WHERE id = ?", (o["entity_id"],)).fetchone()
            if o["entity_type"] == "extracted_item"
            else conn.execute(
                "SELECT *, description AS display_value FROM obligations WHERE id = ?", (o["entity_id"],)
            ).fetchone()
        )
        if not item:
            continue
        options.append(
            {
                "entity_type": o["entity_type"],
                "entity_id": o["entity_id"],
                "display_value": item["display_value"],
                "review_status": item["review_status"],
                "citations": citations_for(conn, o["entity_type"], [o["entity_id"]])[o["entity_id"]],
            }
        )
    return {
        "id": row["id"],
        "contract_id": contract["id"],
        "contract_name": contract["name"],
        "contract_version_id": row["contract_version_id"],
        "kind": row["kind"],
        "field_name": row["field_name"],
        "question": row["question"],
        "status": row["status"],
        "options": options,
        "citations": citations_for(conn, "clarification_question", [row["id"]])[row["id"]],
        "resolution": loads(row["resolution_json"]),
        "resolution_note": row["resolution_note"],
        "created_at": row["created_at"],
        "resolved_at": row["resolved_at"],
    }


def list_clarifications(conn: sqlite3.Connection, contract_id: str | None, status: str | None) -> list[dict]:
    version_ids = latest_version_ids(conn)
    sql = f"""SELECT q.* FROM clarification_questions q JOIN contract_versions v ON v.id = q.contract_version_id
              WHERE q.contract_version_id IN ({placeholders(version_ids)})"""
    params: list = list(version_ids)
    if contract_id:
        sql += " AND v.contract_id = ?"
        params.append(contract_id)
    if status:
        sql += " AND q.status = ?"
        params.append(status)
    rows = conn.execute(sql + " ORDER BY q.created_at", params).fetchall()
    return [serialize_clarification(conn, r) for r in rows]


def resolve_clarification(conn: sqlite3.Connection, clarification_id: str, body: dict) -> dict:
    row = conn.execute("SELECT * FROM clarification_questions WHERE id = ?", (clarification_id,)).fetchone()
    if not row:
        raise not_found("CLARIFICATION_NOT_FOUND", "Clarification")
    if row["status"] != "open":
        raise AppError("CLARIFICATION_ALREADY_CLOSED", "This clarification is already closed.", 409)
    action, note = body.get("action"), body.get("note")
    version_id = row["contract_version_id"]
    option_ids = [
        r["entity_id"]
        for r in conn.execute(
            "SELECT entity_id FROM clarification_options WHERE clarification_id = ? AND entity_type = 'extracted_item'",
            (clarification_id,),
        )
    ]
    now = utc_now()

    def set_item(entity_id: str, status: str) -> None:
        item = _get_entity(conn, "extracted_item", entity_id)
        if item["review_status"] == status:
            return
        _set_status(conn, "extracted_item", entity_id, status)
        _record(
            conn,
            "extracted_item",
            entity_id,
            "approve" if status == "approved" else "reject",
            item["review_status"],
            status,
            None,
            None,
            note,
            clarification_id,
        )

    if action == "select":
        selected = body.get("entity_id")
        if selected not in option_ids:
            raise AppError("VALIDATION_ERROR", "entity_id must be one of the clarification's options.", 422)
        for entity_id in option_ids:
            set_item(entity_id, "approved" if entity_id == selected else "rejected")
        resolution, new_status = {"action": "select", "entity_id": selected}, "resolved"
    elif action == "custom":
        field_name = row["field_name"]
        if not field_name:
            raise AppError("VALIDATION_ERROR", "This clarification has no field to set a value for.", 422)
        value = validate_item_value(field_name, body.get("value"))
        for entity_id in option_ids:
            set_item(entity_id, "rejected")
        item_id = new_id("itm")
        conn.execute(
            """INSERT INTO extracted_items (id, contract_version_id, field_name, value_json, original_value_json,
                   display_value, confidence, review_status, ambiguity_note, origin, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'high', 'edited', NULL, 'human', ?, ?)""",
            (
                item_id,
                version_id,
                field_name,
                dumps(value),
                dumps(value),
                templates.display_value(field_name, value),
                now,
                now,
            ),
        )
        _record(conn, "extracted_item", item_id, "edit", "pending", "edited", None, value, note, clarification_id)
        resolution, new_status = {"action": "custom", "entity_id": item_id, "value": value}, "resolved"
    elif action == "dismiss":
        resolution, new_status = {"action": "dismiss"}, "dismissed"
    else:
        raise AppError("VALIDATION_ERROR", "action must be select, custom or dismiss", 422)

    conn.execute(
        "UPDATE clarification_questions SET status = ?, resolution_json = ?, resolution_note = ?, resolved_at = ?"
        " WHERE id = ?",
        (new_status, dumps(resolution), note, now, clarification_id),
    )
    calculation_service.recalculate(conn, version_id)
    _touch_contract(conn, version_id)
    conn.commit()
    updated = conn.execute("SELECT * FROM clarification_questions WHERE id = ?", (clarification_id,)).fetchone()
    contract = _contract_for_version(conn, version_id)
    return {
        "clarification": serialize_clarification(conn, updated),
        "renewal": calculation_service.serialize_renewal(conn, version_id, contract),
    }


# ---------------------------------------------------------------- citations


def citation_detail(conn: sqlite3.Connection, citation_id: str) -> dict:
    row = conn.execute(
        """SELECT c.*, v.contract_id, v.version_number, v.file_name FROM citations c
           JOIN contract_versions v ON v.id = c.contract_version_id WHERE c.id = ?""",
        (citation_id,),
    ).fetchone()
    if not row:
        raise not_found("CITATION_NOT_FOUND", "Citation")
    segment = before = after = None
    if row["segment_id"]:
        seg = conn.execute("SELECT * FROM document_segments WHERE id = ?", (row["segment_id"],)).fetchone()
        if seg:
            highlight = None
            if row["validation_status"] != "not_found" and row["char_start"] is not None:
                highlight = {"start": row["char_start"], "end": row["char_end"]}
            segment = {"text": seg["text"], "highlight": highlight}
            neighbours = {
                r["seq"]: r["text"]
                for r in conn.execute(
                    "SELECT seq, text FROM document_segments WHERE contract_version_id = ? AND seq IN (?, ?)",
                    (seg["contract_version_id"], seg["seq"] - 1, seg["seq"] + 1),
                )
            }
            before, after = neighbours.get(seg["seq"] - 1), neighbours.get(seg["seq"] + 1)
    return {
        "id": row["id"],
        "contract_id": row["contract_id"],
        "contract_version_id": row["contract_version_id"],
        "version_number": row["version_number"],
        "file_name": row["file_name"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "page": row["page"],
        "section": row["section"],
        "source_text": row["source_text"],
        "validation_status": row["validation_status"],
        "segment": segment,
        "context_before": before,
        "context_after": after,
    }


def recent(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        """SELECT r.*, c.id AS contract_id, c.name AS contract_name,
                  COALESCE(i.field_name, 'obligation') AS field_name, o.description AS obligation_description
           FROM reviews r
           LEFT JOIN extracted_items i ON r.entity_type = 'extracted_item' AND i.id = r.entity_id
           LEFT JOIN obligations o ON r.entity_type = 'obligation' AND o.id = r.entity_id
           JOIN contract_versions v ON v.id = COALESCE(i.contract_version_id, o.contract_version_id)
           JOIN contracts c ON c.id = v.contract_id
           ORDER BY r.reviewed_at DESC, r.rowid DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [
        {
            **_serialize_review(r),
            "contract_id": r["contract_id"],
            "contract_name": r["contract_name"],
            "label": r["obligation_description"] or FIELD_LABELS.get(r["field_name"], r["field_name"]),
        }
        for r in rows
    ]


def entity_detail(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> dict:
    """One reviewable item plus its contract/version context (for the review screen)."""
    row = _get_entity(conn, entity_type, entity_id)
    version = conn.execute(
        """SELECT v.id, v.version_number, v.contract_id, c.name FROM contract_versions v
           JOIN contracts c ON c.id = v.contract_id WHERE v.id = ?""",
        (row["contract_version_id"],),
    ).fetchone()
    latest = conn.execute(
        "SELECT MAX(version_number) FROM contract_versions WHERE contract_id = ?", (version["contract_id"],)
    ).fetchone()[0]
    return {
        "entity_type": entity_type,
        "item": serialize_entity(conn, entity_type, entity_id),
        "contract_id": version["contract_id"],
        "contract_name": version["name"],
        "version_number": version["version_number"],
        "is_latest_version": version["version_number"] == latest,
    }
