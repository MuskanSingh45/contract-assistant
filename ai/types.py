"""Shared data types between backend/ and ai/.

backend/ may import from ai/; ai/ must never import from backend/.
Field names and enum values match db/migrations/001_initial.sql and docs/ai/extraction.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Segment:
    """One citable piece of normalized document text. Produced by backend/documents."""

    seq: int  # 1-based; shown to the model as f"S{seq}"
    page: int | None  # 1-based; None for DOCX/TXT
    section: str | None  # nearest heading, e.g. "2.2 Renewal"
    text: str  # normalized text (see ai/text.py normalize_text)


@dataclass
class Citation:
    segment_seq: int
    source_text: str  # quote as returned by the model
    char_start: int | None  # offsets into Segment.text; None when not_found
    char_end: int | None
    validation_status: str  # 'verified' | 'approximate' | 'not_found'


@dataclass
class ExtractedCandidate:
    """A merged, validated candidate for extracted_items."""

    # party | effective_date | expiration_date | initial_term | renewal_terms | notice_period | termination_clause
    field_name: str
    value: dict[str, Any]  # shape per docs/api/contracts.md
    confidence: str  # high | medium | low (already downgraded by validators)
    ambiguity_note: str | None
    citations: list[Citation] = field(default_factory=list)


@dataclass
class ObligationCandidate:
    description: str
    responsible_party: str | None
    frequency: str | None  # one_time | monthly | quarterly | annually | other | None
    frequency_text: str | None
    due_rule: dict[str, Any]  # {"basis": ..., "offset_days": int}
    due_date_text: str | None
    confidence: str
    ambiguity_note: str | None
    original_value: dict[str, Any]  # the model's raw `value` object for this obligation
    citations: list[Citation] = field(default_factory=list)


@dataclass
class ClarificationDraft:
    kind: str  # conflict | ambiguity | missing
    field_name: str | None
    question: str
    option_indexes: list[int]  # indexes into AnalysisResult.items
    citations: list[Citation] = field(default_factory=list)


@dataclass
class AnalysisResult:
    items: list[ExtractedCandidate]
    obligations: list[ObligationCandidate]
    clarifications: list[ClarificationDraft]
    model_name: str
    prompt_version: str  # e.g. "terms-v1+obligations-v1"
    stats: dict[str, Any] = field(
        default_factory=dict
    )  # windows, retries, dropped_unsupported, citations_not_found, seconds
