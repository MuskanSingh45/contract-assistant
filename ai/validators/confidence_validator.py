"""Confidence downgrades (docs/ai/confidence.md). Confidence is only ever lowered."""

from __future__ import annotations

from ai.types import Citation

_RANK = {"low": 0, "medium": 1, "high": 2}


def cap(confidence: str, maximum: str | None) -> str:
    if maximum is None:
        return confidence
    return confidence if _RANK.get(confidence, 0) <= _RANK[maximum] else maximum


def highest(a: str, b: str) -> str:
    return a if _RANK.get(a, 0) >= _RANK.get(b, 0) else b


def adjust_confidence(confidence: str, citations: list[Citation], ambiguity_note: str | None) -> str:
    """Apply citation and ambiguity caps. Date caps are applied by the business validator."""
    statuses = {c.validation_status for c in citations}
    if statuses == {"not_found"}:
        confidence = cap(confidence, "low")
    elif "verified" not in statuses and "approximate" in statuses:
        confidence = cap(confidence, "medium")
    if ambiguity_note:
        confidence = cap(confidence, "medium")
    return confidence
