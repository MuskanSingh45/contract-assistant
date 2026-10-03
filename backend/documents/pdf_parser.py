import pymupdf

from backend.documents.normalizer import RawParagraph


def read_pdf(path: str) -> tuple[list[RawParagraph], int]:
    """One RawParagraph per text block, in reading order, with 1-based page numbers.
    Raises on unreadable or encrypted files."""
    with pymupdf.open(path, filetype="pdf") as doc:
        if doc.needs_pass:
            raise ValueError("PDF is encrypted")
        paragraphs = [
            RawParagraph(text=block[4], page=page.number + 1)
            for page in doc
            for block in page.get_text("blocks", sort=True)
            if block[6] == 0  # text block (1 = image)
        ]
        return paragraphs, doc.page_count
