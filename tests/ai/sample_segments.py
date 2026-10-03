"""Build Segment lists from the plain-text samples (independent of backend/documents)."""

from __future__ import annotations

import re
from pathlib import Path

from ai.text import normalize_text
from ai.types import Segment

ROOT = Path(__file__).resolve().parents[2]
_SUBSECTION = re.compile(r"^(\d+(?:\.\d+)+)\s+([A-Z][\w ]{0,40}?)\.\s")


def _is_heading(block: str) -> bool:
    return "\n" not in block and len(block) <= 60 and not block.endswith(".")


def segments_from_text(text: str) -> list[Segment]:
    segments: list[Segment] = []
    heading: str | None = None
    for block in (b.strip() for b in re.split(r"\n\s*\n", text)):
        if not block:
            continue
        if _is_heading(block):
            heading = normalize_text(block)
            continue
        normalized = normalize_text(block)
        match = _SUBSECTION.match(normalized)
        section = f"{match.group(1)} {match.group(2)}" if match else heading
        segments.append(Segment(len(segments) + 1, None, section, normalized))
    return segments


def load_sample(relative: str) -> list[Segment]:
    return segments_from_text((ROOT / "contracts" / relative).read_text(encoding="utf-8"))
