"""Clarification question templates (docs/ai/clarification.md). Pure functions, no LLM.

The backend also calls these (e.g. display_value after a human edit, missing_term_question
after date calculation).
"""

from __future__ import annotations

import json
from typing import Any

from ai.types import ClarificationDraft, ExtractedCandidate

FIELD_LABELS: dict[str, str] = {
    "party": "party",
    "effective_date": "effective date",
    "expiration_date": "expiration date",
    "initial_term": "initial term",
    "renewal_terms": "renewal terms",
    "notice_period": "notice period",
    "termination_clause": "termination clause",
}

DATE_INPUT_FIELDS = (
    "effective_date",
    "expiration_date",
    "initial_term",
    "renewal_terms",
    "notice_period",
)

_COUNT_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
_SINGULAR_UNITS = {
    "days": "day",
    "months": "month",
    "years": "year",
    "business_days": "business day",
}
_ANCHORS = {"expiration_date": "before expiration", "renewal_date": "before renewal"}
_PURPOSES = {"non_renewal": "non-renewal", "termination": "termination"}


def _label(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name.replace("_", " "))


def _plural(label: str) -> str:
    return label if label.endswith("s") else f"{label}s"


def _period(value: Any, unit: str | None) -> str:
    if unit is None:
        return str(value)
    if value == 1:
        return f"1 {_SINGULAR_UNITS.get(unit, unit)}"
    return f"{value} {unit.replace('_', ' ')}"


def display_value(field_name: str, value: dict[str, Any]) -> str:
    """Human-readable rendering of an extracted value (extracted_items.display_value)."""
    if field_name == "party":
        role = value.get("role")
        return f"{value.get('name', '')} ({role})" if role else str(value.get("name", ""))
    if field_name in ("effective_date", "expiration_date"):
        return str(value.get("date") or value.get("date_text") or "")
    if field_name == "initial_term":
        return _period(value.get("value"), value.get("unit"))
    if field_name == "renewal_terms":
        kind = value.get("type")
        if kind == "none":
            return "No renewal"
        text = str(kind or "").capitalize()
        if value.get("period_value") is not None:
            text += f", {_period(value['period_value'], value.get('period_unit'))}"
        return text
    if field_name == "notice_period":
        text = _period(value.get("value"), value.get("unit"))
        anchor = _ANCHORS.get(value.get("anchor"))
        if anchor:
            text += f" {anchor}"
        purpose = _PURPOSES.get(value.get("purpose"))
        if purpose:
            text += f" ({purpose})"
        return text
    if field_name == "termination_clause":
        return str(value.get("summary", ""))
    return json.dumps(value, sort_keys=True)


def conflict_question(field_name: str, options: list[tuple[str, str | None]]) -> str:
    """options = [(display_value, section or None), ...]"""
    label = _label(field_name)
    count = _COUNT_WORDS.get(len(options), str(len(options)))
    parts = [f"{value} in {section}" if section else value for value, section in options]
    return (
        f"{count} sections specify different {_plural(label)} ({', '.join(parts)}). "
        f"Which provision should be treated as the applicable {label} rule?"
    )


def ambiguity_question(field_name: str, display_value: str, ambiguity_note: str) -> str:
    note = ambiguity_note.strip().rstrip(".")
    return (
        f"The {_label(field_name)} may be ambiguous: {note}. "
        f"Please confirm or correct the extracted value '{display_value}'."
    )


def missing_term_question() -> str:
    return (
        "No expiration date or initial term was found. Enter the expiration date to enable "
        "deadline calculation, or dismiss if the contract has no fixed term."
    )


def ambiguity_drafts(items: list[ExtractedCandidate], in_conflict: set[int]) -> list[ClarificationDraft]:
    """One ambiguity clarification per date-input item with an ambiguity_note that is not
    already part of a conflict. Notice periods with anchor 'other' are not date inputs."""
    drafts = []
    for index, item in enumerate(items):
        if item.field_name not in DATE_INPUT_FIELDS or not item.ambiguity_note:
            continue
        if index in in_conflict:
            continue
        if item.field_name == "notice_period" and item.value.get("anchor") == "other":
            continue
        question = ambiguity_question(
            item.field_name,
            display_value(item.field_name, item.value),
            item.ambiguity_note,
        )
        drafts.append(
            ClarificationDraft(
                kind="ambiguity",
                field_name=item.field_name,
                question=question,
                option_indexes=[index],
                citations=list(item.citations),
            )
        )
    return drafts
