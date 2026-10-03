"""Terms extraction for one window (prompt extraction/terms.txt, schema extraction.json)."""

from __future__ import annotations

import logging
from typing import Any

from ai.llm.client import LLMClient
from ai.llm.structured_output import (
    load_prompt,
    load_schema,
    render_prompt,
    request_structured,
)
from ai.types import Citation, ExtractedCandidate, Segment
from ai.validators.citation_validator import validate_evidence
from ai.validators.confidence_validator import adjust_confidence, cap
from ai.validators.extraction_validator import (
    check_term_value,
    check_value_against_citations,
)

logger = logging.getLogger(__name__)

PROMPT = "extraction/terms.txt"
SCHEMA = "extraction.json"

# schema key -> extracted_items.field_name
FIELD_NAMES = {
    "parties": "party",
    "effective_date": "effective_date",
    "expiration_date": "expiration_date",
    "initial_term": "initial_term",
    "renewal_terms": "renewal_terms",
    "notice_period": "notice_period",
    "termination_clause": "termination_clause",
}


def ground(raw: dict[str, Any], window: dict[int, Segment], stats: dict[str, Any]) -> list[Citation] | None:
    """Validate a candidate's evidence. None (and counted as dropped) if nothing remains."""
    citations = validate_evidence(raw.get("evidence") or [], window)
    if not citations:
        stats["dropped_unsupported"] = stats.get("dropped_unsupported", 0) + 1
        logger.info(
            "Dropped candidate without supported evidence",
            extra={"event": "extraction.dropped", "reason": "unsupported_evidence"},
        )
        return None
    stats["citations_not_found"] = stats.get("citations_not_found", 0) + sum(
        c.validation_status == "not_found" for c in citations
    )
    return citations


CONTEXT_CHARS = 150


def _context(citation: Citation, window: dict[int, Segment]) -> str:
    """The cited span plus some surrounding text (the model's quotes are often terse)."""
    if citation.char_start is None or citation.char_end is None:
        return citation.source_text
    text = window[citation.segment_seq].text
    return text[max(0, citation.char_start - CONTEXT_CHARS) : citation.char_end + CONTEXT_CHARS]


def _append_note(note: str | None, extra: str | None) -> str | None:
    if not extra:
        return note
    return f"{note.rstrip('. ')}. {extra}" if note else extra


def extract_terms(
    client: LLMClient,
    window_text: str,
    window: dict[int, Segment],
    stats: dict[str, Any],
) -> list[ExtractedCandidate]:
    _, template = load_prompt(PROMPT)
    data = request_structured(client, render_prompt(template, window_text), load_schema(SCHEMA), stats)
    candidates = []
    for key, field_name in FIELD_NAMES.items():
        for raw in data.get(key, []):
            value = dict(raw["value"])
            keep, date_cap, extra_note = check_term_value(field_name, value)
            if not keep:
                stats["dropped_invalid"] = stats.get("dropped_invalid", 0) + 1
                logger.info(
                    "Dropped invalid %s candidate: %s",
                    field_name,
                    value,
                    extra={"event": "extraction.dropped", "field": field_name, "reason": "invalid_value"},
                )
                continue
            citations = ground(raw, window, stats)
            if citations is None:
                continue
            keep, value, quote_note = check_value_against_citations(
                field_name, value, [_context(c, window) for c in citations]
            )
            if not keep:
                stats["dropped_invalid"] = stats.get("dropped_invalid", 0) + 1
                logger.info(
                    "Dropped %s not supported by its quotes: %s",
                    field_name,
                    value,
                    extra={"event": "extraction.dropped", "field": field_name, "reason": "not_supported_by_quotes"},
                )
                continue
            note = _append_note(raw.get("ambiguity_note") or None, extra_note)
            note = _append_note(note, quote_note)
            confidence = cap(adjust_confidence(raw["confidence"], citations, note), date_cap)
            candidates.append(ExtractedCandidate(field_name, value, confidence, note, citations))
    return candidates
