"""Rendering Slides as images, for Citations and the Evaluation Set review page."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from course_qa.ingest import SLIDES_FILE


class UnknownSlide(LookupError):
    """The Slide isn't in the current ingest (or was removed as a Duplicate Slide)."""


class SlideImages:
    def __init__(self, index_dir: Path, lectures_dir: Path):
        self._lectures_dir = Path(lectures_dir)
        slides = json.loads((Path(index_dir) / SLIDES_FILE).read_text(encoding="utf-8"))
        self._sources = {(s["lecture"], s["slide"]): s["source"] for s in slides}

    def render_png(self, lecture: str, slide: int, width: int = 960) -> bytes:
        """The Slide's page as a PNG, ``width`` pixels wide."""
        source = self._sources.get((lecture, slide))
        if source is None:
            raise UnknownSlide(f"{lecture} — Slide {slide} is not in the index")
        with pymupdf.open(self._lectures_dir / source) as doc:
            page = doc[slide - 1]
            zoom = width / page.rect.width
            return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
