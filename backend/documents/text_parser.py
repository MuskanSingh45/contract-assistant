import re

from backend.documents.normalizer import RawParagraph

_BLANK_LINES = re.compile(r"\n\s*\n")


def read_text(path: str) -> list[RawParagraph]:
    """Paragraphs separated by blank lines. Raises UnicodeDecodeError/OSError on unreadable files."""
    with open(path, encoding="utf-8-sig") as f:
        content = f.read().replace("\r\n", "\n").replace("\r", "\n")
    return [RawParagraph(text=p) for p in _BLANK_LINES.split(content) if p.strip()]
