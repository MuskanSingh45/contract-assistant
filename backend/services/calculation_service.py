"""Builds date-engine inputs from a version's extracted items and stores the results.

Rules: docs/architecture/date-calculation.md. All arithmetic is in backend/utils/dates.py.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from backend.services.common import (
    DATE_INPUT_FIELDS,
    dumps,
    iso,
    loads,
    new_id,
    to_date,
    today,
    utc_now,
)
from backend.utils import dates

RENEWAL_RELEVANT_ANCHORS = ("expiration_date", "renewal_date")


@dataclass
class SelectedInputs:
    inputs: dates.RenewalInputs
    used_item_ids: list[str]
    inputs_reviewed: bool
    candidates: dict[str, list[sqlite3.Row]]  # non-rejected items per date-input field


def _comparable(field_name: str, value: dict) -> tuple:
    if field_name in ("effective_date", "expiration_date"):
        return (value.get("date") or value.get("date_text"),)
    if field_name == "initial_term":
        return (value.get("value"), value.get("unit"))
    if field_name == "renewal_terms":
        return (value.get("type"), value.get("period_value"), value.get("period_unit"))
    if field_name == "notice_period":
        return (value.get("value"), value.get("unit"), value.get("anchor"))
    return (dumps(value),)


def _item_date(value: dict) -> date | None:
    if value.get("date"):
        try:
            return date.fromisoformat(value["date"])
        except ValueError:
            return None
    return dates.parse_date_text(value.get("date_text"))


def select_inputs(conn: sqlite3.Connection, version_id: str) -> SelectedInputs:
    rows = conn.execute(
        f"""SELECT * FROM extracted_items WHERE contract_version_id = ? AND review_status != 'rejected'
            AND field_name IN ({",".join("?" for _ in DATE_INPUT_FIELDS)}) ORDER BY created_at, id""",
        (version_id, *DATE_INPUT_FIELDS),
    ).fetchall()

    candidates: dict[str, list[sqlite3.Row]] = {f: [] for f in DATE_INPUT_FIELDS}
    for row in rows:
        value = loads(row["value_json"])
        if row["field_name"] == "notice_period" and value.get("anchor") not in RENEWAL_RELEVANT_ANCHORS:
            continue
        candidates[row["field_name"]].append(row)

    chosen: dict[str, dict] = {}
    conflicted: set[str] = set()
    used: list[sqlite3.Row] = []
    for field_name, items in candidates.items():
        distinct = {_comparable(field_name, loads(r["value_json"])) for r in items}
        if len(distinct) > 1:
            conflicted.add(field_name)
        elif items:
            chosen[field_name] = loads(items[0]["value_json"])
            used.extend(items)

    # A notice period anchored to "other" only matters when no renewal-relevant one exists.
    if "notice_period" not in chosen and "notice_period" not in conflicted:
        other = conn.execute(
            """SELECT * FROM extracted_items WHERE contract_version_id = ? AND field_name = 'notice_period'
               AND review_status != 'rejected' ORDER BY created_at LIMIT 1""",
            (version_id,),
        ).fetchone()
        if other:
            chosen["notice_period"] = loads(other["value_json"])
            used.append(other)

    def period(v: dict | None, value_key: str, unit_key: str) -> tuple[int, str] | None:
        if not v or not v.get(value_key) or not v.get(unit_key):
            return None
        return (int(v[value_key]), v[unit_key])

    notice = chosen.get("notice_period")
    renewal = chosen.get("renewal_terms")
    inputs = dates.RenewalInputs(
        effective_date=_item_date(chosen["effective_date"]) if "effective_date" in chosen else None,
        expiration_date=_item_date(chosen["expiration_date"]) if "expiration_date" in chosen else None,
        initial_term=period(chosen.get("initial_term"), "value", "unit"),
        renewal_type=renewal.get("type") if renewal else None,
        renewal_period=period(renewal, "period_value", "period_unit"),
        notice_period=(int(notice["value"]), notice["unit"], notice["anchor"]) if notice else None,
        conflicted_fields=frozenset(conflicted),
    )
    return SelectedInputs(
        inputs=inputs,
        used_item_ids=[r["id"] for r in used],
        inputs_reviewed=bool(used) and all(r["review_status"] in ("approved", "edited") for r in used),
        candidates=candidates,
    )


def recalculate(conn: sqlite3.Connection, version_id: str, ref: date | None = None) -> dates.RenewalResult:
    """Recompute the renewal row and calculated obligation due dates. Caller commits."""
    ref = ref or today()
    selected = select_inputs(conn, version_id)
    result = dates.calculate_renewal(selected.inputs, ref)
    conn.execute("DELETE FROM renewals WHERE contract_version_id = ?", (version_id,))
    conn.execute(
        """INSERT INTO renewals (id, contract_version_id, effective_date, expiration_date, expiration_source,
               renewal_type, renewal_period_value, renewal_period_unit, current_term_end,
               notice_period_value, notice_period_unit, notice_anchor, notice_deadline,
               calculation_status, calculation_note, calculated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            new_id("ren"),
            version_id,
            iso(result.effective_date),
            iso(result.expiration_date),
            result.expiration_source,
            result.renewal_type,
            result.renewal_period_value,
            result.renewal_period_unit,
            iso(result.current_term_end),
            result.notice_period_value,
            result.notice_period_unit,
            result.notice_anchor,
            iso(result.notice_deadline),
            result.calculation_status,
            result.calculation_note,
            utc_now(),
        ),
    )
    _recalculate_obligations(conn, version_id, result, ref)
    return result


def _recalculate_obligations(
    conn: sqlite3.Connection, version_id: str, renewal: dates.RenewalResult, ref: date
) -> None:
    rows = conn.execute(
        "SELECT id, due_rule_json, frequency, due_date, due_date_source FROM obligations WHERE contract_version_id = ?",
        (version_id,),
    ).fetchall()
    for row in rows:
        rule = loads(row["due_rule_json"])
        due_date_text = rule.get("due_date_text") if rule else None
        due, source = dates.obligation_due_date(
            due_rule=rule,
            frequency=row["frequency"],
            due_date_text=due_date_text,
            effective_date=renewal.effective_date,
            notice_deadline=renewal.notice_deadline,
            today=ref,
        )
        conn.execute(
            "UPDATE obligations SET due_date = ?, due_date_source = ? WHERE id = ?",
            (iso(due), source, row["id"]),
        )


def serialize_renewal(
    conn: sqlite3.Connection, version_id: str, contract: sqlite3.Row, ref: date | None = None
) -> dict | None:
    ref = ref or today()
    row = conn.execute("SELECT * FROM renewals WHERE contract_version_id = ?", (version_id,)).fetchone()
    if not row:
        return None
    selected = select_inputs(conn, version_id)
    deadline = to_date(row["notice_deadline"])
    term_end = to_date(row["current_term_end"])
    has_period = row["renewal_period_value"] is not None
    has_notice = row["notice_period_value"] is not None
    return {
        "contract_id": contract["id"],
        "contract_name": contract["name"],
        "contract_version_id": version_id,
        "effective_date": row["effective_date"],
        "expiration_date": row["expiration_date"],
        "expiration_source": row["expiration_source"],
        "renewal_type": row["renewal_type"],
        "renewal_period": {"value": row["renewal_period_value"], "unit": row["renewal_period_unit"]}
        if has_period
        else None,
        "current_term_end": row["current_term_end"],
        "notice_period": {
            "value": row["notice_period_value"],
            "unit": row["notice_period_unit"],
            "anchor": row["notice_anchor"],
        }
        if has_notice
        else None,
        "notice_deadline": row["notice_deadline"],
        "days_until_notice_deadline": dates.days_until(deadline, ref),
        "days_until_term_end": dates.days_until(term_end, ref),
        "lifecycle_status": dates.lifecycle_status(term_end, deadline, ref, _window()),
        "calculation_status": row["calculation_status"],
        "calculation_note": row["calculation_note"],
        "inputs_reviewed": selected.inputs_reviewed,
        "input_item_ids": selected.used_item_ids,
    }


def _window() -> int:
    from backend.core.config import settings

    return settings.upcoming_window_days
