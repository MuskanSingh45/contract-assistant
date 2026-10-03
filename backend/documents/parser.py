"""Document parsing entry point: PDF / DOCX / TXT -> ordered Segments (docs/ai/pipeline.md §1)."""

import logging
import os

from ai.types import Segment
from backend.documents.docx_parser import read_docx
from backend.documents.normalizer import build_segments
from backend.documents.pdf_parser import read_pdf
from backend.documents.text_parser import read_text

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEXT_MIME = "text/plain"
MIN_TEXT_CHARS = 20


class DocumentParseError(Exception):
    """Corrupt, encrypted or unreadable document (DOCUMENT_PARSE_FAILED)."""


class NoExtractableText(Exception):
    """Document opened but contains no usable text, e.g. a scanned PDF (NO_EXTRACTABLE_TEXT)."""


def detect_mime_type(filename: str, head: bytes) -> str | None:
    """Accept only .pdf / .docx whose leading bytes match the format signature."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf" and head.startswith(b"%PDF"):
        return PDF_MIME
    if ext == ".docx" and head.startswith(b"PK\x03\x04"):
        return DOCX_MIME
    return None


def parse_document(path: str, mime_type: str) -> tuple[list[Segment], int | None]:
    """Return (segments, page_count); page_count is None for DOCX/TXT."""
    page_count: int | None = None
    try:
        if mime_type == PDF_MIME:
            paragraphs, page_count = read_pdf(path)
        elif mime_type == DOCX_MIME:
            paragraphs = read_docx(path)
        elif mime_type == TEXT_MIME:
            paragraphs = read_text(path)
        else:
            raise DocumentParseError(f"Unsupported mime type: {mime_type}")
    except DocumentParseError:
        raise
    except Exception as exc:
        logger.warning("Document parse failed (%s): %s", mime_type, exc)
        raise DocumentParseError(str(exc)) from exc

    segments = build_segments(paragraphs)
    if sum(1 for s in segments for c in s.text if not c.isspace()) < MIN_TEXT_CHARS:
        raise NoExtractableText("No extractable text found")
    return segments, page_count
