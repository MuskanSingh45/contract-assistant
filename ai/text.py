"""Text normalization shared by document parsing (backend/documents) and citation validation (ai/validators).

Invariant: Segment.text is stored as normalize_text(raw). For any normalized string s,
normalize_for_match(s) == s.lower() has the same length as s, so character offsets found
when matching against normalize_for_match(segment.text) are valid offsets into segment.text.
"""

import re

_REPLACEMENTS = {
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    "–": "-",
    "—": "-",
    "−": "-",
    " ": " ",
    " ": " ",
    " ": " ",
    "­": "",  # soft hyphen
    "ﬁ": "fi",
    "ﬂ": "fl",
}
_TRANSLATION = str.maketrans(_REPLACEMENTS)
_HYPHEN_BREAK = re.compile(r"(\w)-\s*\n\s*(\w)")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(raw: str) -> str:
    """Normalize text for storage: straight quotes/dashes, words rejoined across hyphenated
    line breaks, every whitespace run collapsed to one space, stripped."""
    text = raw.translate(_TRANSLATION)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    return _WHITESPACE.sub(" ", text).strip()


def normalize_for_match(text: str) -> str:
    """Normalize for case-insensitive comparison. Length-preserving for already-normalized text."""
    return normalize_text(text).lower()
