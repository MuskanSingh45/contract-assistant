"""A scripted LLM client and candidate builders for pipeline tests (no Ollama needed)."""

from __future__ import annotations

import json
from typing import Any

EMPTY_TERMS: dict[str, list] = {
    "parties": [],
    "effective_date": [],
    "expiration_date": [],
    "initial_term": [],
    "renewal_terms": [],
    "notice_period": [],
    "termination_clause": [],
}


class FakeClient:
    """Returns queued responses; terms and obligation calls are told apart by the schema."""

    model = "fake-model"

    def __init__(self, terms: list[Any] | None = None, obligations: list[Any] | None = None):
        self.queues = {
            "terms": list(terms or []),
            "obligations": list(obligations or []),
        }
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        kind = "obligations" if "obligations" in schema["properties"] else "terms"
        self.calls.append((kind, messages))
        queue = self.queues[kind]
        response = queue.pop(0) if queue else ({"obligations": []} if kind == "obligations" else EMPTY_TERMS)
        return response if isinstance(response, str) else json.dumps(response)


def terms(**fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {**EMPTY_TERMS, **fields}


def cand(value: dict[str, Any], seg: str, quote: str, confidence: str = "high", note=None):
    return {
        "value": value,
        "confidence": confidence,
        "evidence": [{"segment_id": seg, "quote": quote}],
        "ambiguity_note": note,
    }


def obligation(description: str, party: str | None, seg: str, quote: str) -> dict[str, Any]:
    return cand(
        {
            "description": description,
            "responsible_party": party,
            "frequency": "quarterly",
            "frequency_text": None,
            "due_rule": {"basis": "calendar_period_end", "offset_days": 30},
            "due_date_text": None,
        },
        seg,
        quote,
    )
