from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest


def make_lecture(path: Path, slides: list[tuple[str, str]]) -> Path:
    """Write a Lecture PDF with one page per (title, body) Slide.

    Titles are set in a large font and bodies in a small one, as real decks are.
    """
    doc = fitz.open()
    for title, body in slides:
        page = doc.new_page()
        page.insert_text((72, 90), title, fontsize=28)
        y = 150
        for line in body.split("\n"):
            page.insert_text((72, y), line, fontsize=14)
            y += 24
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def lectures_dir(tmp_path: Path) -> Path:
    return tmp_path / "lectures"


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    return tmp_path / "index"
