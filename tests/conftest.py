from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

BROKEN_BULLET = ""  # a private-use Wingdings bullet, as real decks extract it

# A Helvetica font whose ToUnicode map turns byte 0x80 into the private-use
# bullet, reproducing how symbol-font bullets come out of real slide decks.
_BROKEN_CMAP = b"""/CIDInit /ProcSet findresource begin 12 dict begin begincmap
/CMapName /Broken def 1 begincodespacerange <00> <FF> endcodespacerange
1 beginbfchar <80> <F0A7> endbfchar
endcmap CMapName currentdict /CMap defineresource pop end end"""


def make_lecture(
    path: Path,
    slides: list[tuple[str, str]],
    *,
    footer: str | None = None,
    page_numbers: bool = False,
) -> Path:
    """Write a Lecture PDF with one page per (title, body) Slide.

    Titles are set in a large font and bodies in a small one, as real decks are.
    Body lines starting with BROKEN_BULLET are drawn with a symbol-font bullet that
    extracts as a private-use character. ``footer`` and ``page_numbers`` add the
    small repeated lines real decks carry at the bottom of each Slide.
    """
    doc = pymupdf.open()
    broken_font = None
    for number, (title, body) in enumerate(slides, start=1):
        page = doc.new_page()
        page.insert_text((72, 90), title, fontsize=28)
        y = 150
        for line in body.split("\n") if body else []:
            if line.startswith(BROKEN_BULLET):
                broken_font = broken_font or _add_broken_font(doc)
                _draw_broken_bullet_line(doc, page, broken_font, line[1:].strip(), y)
            else:
                page.insert_text((72, y), line, fontsize=14)
            y += 24
        if footer:
            page.insert_text((72, 800), footer, fontsize=9)
        if page_numbers:
            page.insert_text((540, 800), str(number), fontsize=9)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def _add_broken_font(doc: pymupdf.Document) -> int:
    cmap = doc.get_new_xref()
    doc.update_object(cmap, "<< >>")
    doc.update_stream(cmap, _BROKEN_CMAP)
    font = doc.get_new_xref()
    doc.update_object(
        font, f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode {cmap} 0 R >>"
    )
    return font


def _draw_broken_bullet_line(doc, page, font_xref: int, text: str, y: float) -> None:
    resources = int(doc.xref_get_key(page.xref, "Resources")[1].split()[0])
    fonts = doc.xref_get_key(resources, "Font")[1]
    if "/FBroken" not in fonts:
        doc.xref_set_key(resources, "Font", fonts[:-2] + f" /FBroken {font_xref} 0 R >>")
    pdf_y = page.rect.height - y
    stream = doc.get_new_xref()
    doc.update_object(stream, "<< >>")
    doc.update_stream(
        stream, f"BT /FBroken 14 Tf 72 {pdf_y} Td (\\200 {text}) Tj ET".encode("latin-1")
    )
    contents = doc.xref_get_key(page.xref, "Contents")[1]
    doc.xref_set_key(page.xref, "Contents", contents[:-1] + f" {stream} 0 R]")


@pytest.fixture
def lectures_dir(tmp_path: Path) -> Path:
    return tmp_path / "lectures"


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    return tmp_path / "index"
