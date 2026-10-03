"""Pipeline entry point used by the backend (docs/ai/pipeline.md)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from rapidfuzz import fuzz

from ai.llm.client import LLMClient, active_config, make_client
from ai.llm.model_config import estimate_tokens, load_config
from ai.llm.structured_output import load_prompt
from ai.pipeline import extraction, obligation_extraction
from ai.pipeline.clarification import ambiguity_drafts
from ai.pipeline.conflict_detection import detect_conflicts, value_key
from ai.types import (
    AnalysisResult,
    Citation,
    ExtractedCandidate,
    ObligationCandidate,
    Segment,
)
from ai.validators.confidence_validator import highest

logger = logging.getLogger(__name__)

OBLIGATION_MERGE_THRESHOLD = 90


def format_segment(segment: Segment) -> str:
    header = f"[S{segment.seq}]"
    if segment.section:
        header += f" ({segment.section})"
    return f"{header}\n{segment.text}"


def build_windows(segments: list[Segment], max_tokens: int) -> list[list[Segment]]:
    """Pack segments in order into windows of <= max_tokens; a segment is never split."""
    windows: list[list[Segment]] = []
    current: list[Segment] = []
    used = 0
    for segment in segments:
        cost = estimate_tokens(format_segment(segment) + "\n\n")
        if current and used + cost > max_tokens:
            windows.append(current)
            current, used = [], 0
        current.append(segment)
        used += cost
    if current:
        windows.append(current)
    return windows


def prompt_version() -> str:
    terms, _ = load_prompt(extraction.PROMPT)
    obligations, _ = load_prompt(obligation_extraction.PROMPT)
    return f"{terms}+{obligations}"


def _union_citations(target: list[Citation], extra: list[Citation]) -> None:
    seen = {(c.segment_seq, c.char_start, c.char_end, c.source_text) for c in target}
    for c in extra:
        key = (c.segment_seq, c.char_start, c.char_end, c.source_text)
        if key not in seen:
            seen.add(key)
            target.append(c)


def _merge_notes(a: str | None, b: str | None) -> str | None:
    if not a or not b or b in a:
        return a or b
    return f"{a.rstrip('. ')}. {b}"


def merge_items(candidates: list[ExtractedCandidate]) -> list[ExtractedCandidate]:
    """Same field + same normalized value -> one item (union citations, highest confidence)."""
    merged: list[ExtractedCandidate] = []
    index: dict[tuple, ExtractedCandidate] = {}
    for cand in candidates:
        key = (cand.field_name, value_key(cand.field_name, cand.value))
        existing = index.get(key)
        if existing is None:
            item = ExtractedCandidate(
                cand.field_name,
                cand.value,
                cand.confidence,
                cand.ambiguity_note,
                list(cand.citations),
            )
            index[key] = item
            merged.append(item)
            continue
        existing.confidence = highest(existing.confidence, cand.confidence)
        existing.ambiguity_note = _merge_notes(existing.ambiguity_note, cand.ambiguity_note)
        _union_citations(existing.citations, cand.citations)
    return merged


def _same_party(a: str | None, b: str | None) -> bool:
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def merge_obligations(
    candidates: list[ObligationCandidate],
) -> list[ObligationCandidate]:
    merged: list[ObligationCandidate] = []
    for cand in candidates:
        for existing in merged:
            if _same_party(existing.responsible_party, cand.responsible_party) and (
                fuzz.token_set_ratio(existing.description.lower(), cand.description.lower())
                >= OBLIGATION_MERGE_THRESHOLD
            ):
                existing.confidence = highest(existing.confidence, cand.confidence)
                existing.ambiguity_note = _merge_notes(existing.ambiguity_note, cand.ambiguity_note)
                _union_citations(existing.citations, cand.citations)
                break
        else:
            merged.append(cand)
    return merged


def analyze(
    segments: list[Segment],
    *,
    on_progress: Callable[[str, int, int], None] | None = None,
    client: LLMClient | None = None,
) -> AnalysisResult:
    """Run extraction over all segments and return validated, merged candidates.

    Raises ai.errors.AIUnavailable / AITimeout / InvalidAIOutput.
    """
    started = time.monotonic()
    # The active provider (primary, or the fallback when the primary is down) also sets the window size.
    config = active_config() if client is None else load_config()
    client = client or make_client(config)
    version = prompt_version()
    stats = {
        "windows": 0,
        "retries": 0,
        "dropped_unsupported": 0,
        "citations_not_found": 0,
    }

    windows = build_windows(segments, config.window_tokens)
    stats["windows"] = len(windows)
    terms: list[ExtractedCandidate] = []
    obligations: list[ObligationCandidate] = []
    for number, window_segments in enumerate(windows, start=1):
        if on_progress:
            on_progress("extracting", number, len(windows))
        window = {s.seq: s for s in window_segments}
        window_text = "\n\n".join(format_segment(s) for s in window_segments)
        terms += extraction.extract_terms(client, window_text, window, stats)
        obligations += obligation_extraction.extract_obligations(client, window_text, window, stats)

    if on_progress:
        on_progress("validating", 0, 0)
    items = merge_items(terms)
    merged_obligations = merge_obligations(obligations)
    by_seq = {s.seq: s for s in segments}
    conflicts = detect_conflicts(items, by_seq)
    in_conflict = {i for draft in conflicts for i in draft.option_indexes}
    clarifications = conflicts + ambiguity_drafts(items, in_conflict)

    stats["seconds"] = round(time.monotonic() - started, 2)
    logger.info("Analysis finished: %s", stats, extra={"event": "pipeline.finished", "stats": stats})
    return AnalysisResult(
        items=items,
        obligations=merged_obligations,
        clarifications=clarifications,
        model_name=getattr(client, "model", config.model),
        prompt_version=version,
        stats=stats,
    )
