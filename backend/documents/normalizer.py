"""Turn raw paragraphs from the format parsers into ordered, normalized Segments.

Heading rules (docs/ai/pipeline.md §1): a style heading (DOCX) or a short numbered /
ALL-CAPS paragraph sets the current section and is not emitted. A clause with an inline
heading ("2.2 Renewal. This Agreement ...") is emitted and sets the section to "2.2 Renewal".
"""

import re
from dataclasses import dataclass

from ai.text import normalize_text
from ai.types import Segment

MAX_SEGMENT_CHARS = 1500
MAX_HEADING_CHARS = 80
MAX_INLINE_HEADING_CHARS = 60

_NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
_INLINE_HEADING = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+([^.]+?)\.\s+\S")
_SENTENCE_BREAK = re.compile(r"(?<=[.;:])\s+")


@dataclass
class RawParagraph:
    text: str
    page: int | None = None
    style_heading: bool = False  # DOCX "Heading*" / "Title" style


def is_heading(text: str) -> bool:
    """Short numbered line or short ALL-CAPS line (text already normalized)."""
    if not text or len(text) > MAX_HEADING_CHARS:
        return False
    if _NUMBERED.match(text):
        # "4.1 Client shall provide access." is a short clause, not a heading: headings don't
        # end like sentences and are only a few words. Misclassifying drops contract text.
        return not text.rstrip().endswith((".", ";", ":")) and len(text.split()) <= 8
    return any(c.isalpha() for c in text) and text == text.upper()


def inline_heading(text: str) -> str | None:
    """'2.2 Renewal. This Agreement ...' -> '2.2 Renewal'."""
    m = _INLINE_HEADING.match(text)
    if not m:
        return None
    heading = f"{m.group(1)} {m.group(2).strip()}"
    return heading if len(heading) <= MAX_INLINE_HEADING_CHARS else None


def split_long(text: str, limit: int = MAX_SEGMENT_CHARS) -> list[str]:
    """Split at sentence boundaries into chunks <= limit; hard-split oversize sentences at spaces."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    for sentence in _SENTENCE_BREAK.split(text):
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit + 1)
            cut = cut if cut > 0 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 1 + len(piece) <= limit:
            chunks[-1] = f"{chunks[-1]} {piece}"
        else:
            chunks.append(piece)
    return chunks


def build_segments(paragraphs: list[RawParagraph]) -> list[Segment]:
    segments: list[Segment] = []
    section: str | None = None
    for para in paragraphs:
        text = normalize_text(para.text)
        if not text:
            continue
        inline = inline_heading(text)
        if inline is None and (para.style_heading or is_heading(text)):
            section = text
            continue
        if inline is not None:
            section = inline
        for chunk in split_long(text):
            segments.append(Segment(seq=len(segments) + 1, page=para.page, section=section, text=chunk))
    return segments
