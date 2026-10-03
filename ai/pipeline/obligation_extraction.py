"""Obligation extraction for one window (prompt extraction/obligations.txt, schema obligation.json)."""

from __future__ import annotations

import copy
import logging
from typing import Any

from ai.llm.client import LLMClient
from ai.llm.structured_output import (
    load_prompt,
    load_schema,
    render_prompt,
    request_structured,
)
from ai.pipeline.extraction import ground
from ai.types import ObligationCandidate, Segment
from ai.validators.confidence_validator import adjust_confidence
from ai.validators.extraction_validator import (
    check_obligation_value,
    is_permission_only,
)

logger = logging.getLogger(__name__)

PROMPT = "extraction/obligations.txt"
SCHEMA = "obligation.json"


def extract_obligations(
    client: LLMClient,
    window_text: str,
    window: dict[int, Segment],
    stats: dict[str, Any],
) -> list[ObligationCandidate]:
    _, template = load_prompt(PROMPT)
    data = request_structured(client, render_prompt(template, window_text), load_schema(SCHEMA), stats)
    candidates = []
    for raw in data.get("obligations", []):
        value = raw["value"]
        if not check_obligation_value(value):
            stats["dropped_invalid"] = stats.get("dropped_invalid", 0) + 1
            continue
        citations = ground(raw, window, stats)
        if citations is None:
            continue
        if is_permission_only([c.source_text for c in citations]):
            stats["dropped_invalid"] = stats.get("dropped_invalid", 0) + 1
            continue
        note = raw.get("ambiguity_note") or None
        candidates.append(
            ObligationCandidate(
                description=value["description"],
                responsible_party=value.get("responsible_party"),
                frequency=value.get("frequency"),
                frequency_text=value.get("frequency_text"),
                due_rule=dict(value["due_rule"]),
                due_date_text=value.get("due_date_text"),
                confidence=adjust_confidence(raw["confidence"], citations, note),
                ambiguity_note=note,
                original_value=copy.deepcopy(value),
                citations=citations,
            )
        )
    return candidates
