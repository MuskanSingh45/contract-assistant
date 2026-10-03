"""Re-export of the shared normalization helpers (ai/ cannot import backend/)."""

from ai.text import normalize_for_match, normalize_text

__all__ = ["normalize_for_match", "normalize_text"]
