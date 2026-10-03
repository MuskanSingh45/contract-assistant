"""Citation grounding: check model quotes against the segments it was shown
(docs/ai/citation-and-review.md)."""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from ai.text import normalize_for_match
from ai.types import Citation, Segment

FUZZY_THRESHOLD = 90


def validate_quote(quote: str, segment: Segment) -> Citation:
    """Match one quote against one segment: verified, approximate or not_found."""
    needle = normalize_for_match(quote).strip("\"' ")
    haystack = normalize_for_match(segment.text)
    if needle:
        start = haystack.find(needle)
        if start >= 0:
            return Citation(segment.seq, quote, start, start + len(needle), "verified")
        alignment = fuzz.partial_ratio_alignment(needle, haystack, score_cutoff=FUZZY_THRESHOLD)
        if alignment is not None and alignment.score >= FUZZY_THRESHOLD:
            return Citation(
                segment.seq,
                quote,
                alignment.dest_start,
                alignment.dest_end,
                "approximate",
            )
    return Citation(segment.seq, quote, None, None, "not_found")


def validate_evidence(evidence: list[dict[str, Any]], window: dict[int, Segment]) -> list[Citation]:
    """Validate every evidence entry; entries naming a segment outside the window are discarded."""
    citations: list[Citation] = []
    for entry in evidence:
        label = str(entry.get("segment_id", ""))
        if not label.startswith("S") or not label[1:].isdigit():
            continue
        segment = window.get(int(label[1:]))
        if segment is None:
            continue
        citations.append(validate_quote(str(entry.get("quote", "")), segment))
    return citations
