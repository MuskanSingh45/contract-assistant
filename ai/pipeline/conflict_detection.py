"""Deterministic conflict detection (docs/ai/conflict-detection.md). No LLM."""

from __future__ import annotations

import re
from typing import Any

from ai.pipeline.clarification import conflict_question, display_value
from ai.text import normalize_for_match
from ai.types import ClarificationDraft, ExtractedCandidate, Segment

SINGLE_VALUED_FIELDS = (
    "effective_date",
    "expiration_date",
    "initial_term",
    "renewal_terms",
    "notice_period",
)
RENEWAL_ANCHORS = ("expiration_date", "renewal_date")

_PUNCT = re.compile(r"[^\w\s]")
_COMPANY_SUFFIX = re.compile(r"(\s+(inc|ltd|llc|corp|corporation|limited))+$")


def normalize_party_name(name: str) -> str:
    text = _PUNCT.sub(" ", normalize_for_match(name))
    text = re.sub(r"\s+", " ", text).strip()
    return _COMPANY_SUFFIX.sub("", text).strip()


def value_key(field_name: str, value: dict[str, Any]) -> tuple:
    """Normalized comparison key (docs/ai/pipeline.md §5)."""
    if field_name == "party":
        return (normalize_party_name(value.get("name", "")),)
    if field_name in ("effective_date", "expiration_date"):
        return (value.get("date") or normalize_for_match(value.get("date_text", "")),)
    if field_name == "initial_term":
        return (value.get("value"), value.get("unit"))
    if field_name == "renewal_terms":
        return (value.get("type"), value.get("period_value"), value.get("period_unit"))
    if field_name == "notice_period":
        return (value.get("value"), value.get("unit"), value.get("anchor"))
    if field_name == "termination_clause":
        return (normalize_for_match(value.get("summary", "")),)
    return (repr(sorted(value.items())),)


def detect_conflicts(items: list[ExtractedCandidate], segments: dict[int, Segment]) -> list[ClarificationDraft]:
    """One conflict clarification per single-valued field with >= 2 different merged values.

    `items` are already merged, so items of the same field have different values.
    """
    drafts = []
    for field_name in SINGLE_VALUED_FIELDS:
        indexes = [
            i
            for i, item in enumerate(items)
            if item.field_name == field_name
            and (field_name != "notice_period" or item.value.get("anchor") in RENEWAL_ANCHORS)
        ]
        if len({value_key(field_name, items[i].value) for i in indexes}) < 2:
            continue
        options = []
        citations = []
        for i in indexes:
            item = items[i]
            first = item.citations[0] if item.citations else None
            segment = segments.get(first.segment_seq) if first else None
            section = segment.section if segment else None
            options.append((display_value(field_name, item.value), section))
            citations.extend(item.citations)
        drafts.append(
            ClarificationDraft(
                kind="conflict",
                field_name=field_name,
                question=conflict_question(field_name, options),
                option_indexes=indexes,
                citations=citations,
            )
        )
    return drafts
