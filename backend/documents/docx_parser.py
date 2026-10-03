import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.documents.normalizer import RawParagraph


def _is_style_heading(paragraph: Paragraph) -> bool:
    name = paragraph.style.name if paragraph.style is not None else ""
    return name.startswith(("Heading", "Title"))


def _row_text(row) -> str:
    cells: list[str] = []
    for cell in row.cells:
        text = cell.text.strip()
        if text and (not cells or cells[-1] != text):  # merged cells repeat their text
            cells.append(text)
    return " | ".join(cells)


def read_docx(path: str) -> list[RawParagraph]:
    """Body paragraphs and table rows in document order. Raises on unreadable files."""
    document = docx.Document(path)
    paragraphs: list[RawParagraph] = []
    for item in document.iter_inner_content():
        if isinstance(item, Table):
            paragraphs.extend(RawParagraph(text=_row_text(row)) for row in item.rows)
        elif item.text.strip():
            paragraphs.append(RawParagraph(text=item.text, style_heading=_is_style_heading(item)))
    return paragraphs
