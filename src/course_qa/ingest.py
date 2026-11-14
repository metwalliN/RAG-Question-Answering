"""Ingest: turn Lecture PDFs into Slides, Passages and a searchable index."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import faiss
import pymupdf

from course_qa.config import CleaningSettings, RetrievalConfig
from course_qa.models import Embedder
from course_qa.passages import Passage

PASSAGES_FILE = "passages.json"
DENSE_INDEX_FILE = "dense.faiss"

# Symbol-font bullets extract as the replacement character or private-use code points.
_BROKEN_GLYPHS = re.compile("[�-]")
# A line holding only bullet or arrow symbols carries no content.
_SYMBOLS_ONLY = re.compile("[\\s•·▪▫◦■□●○►▶➢✓✔*>–—-]*")


@dataclass(frozen=True)
class Slide:
    lecture: str
    number: int  # 1-based page number, as students see it in the PDF
    title: str
    text: str


@dataclass(frozen=True)
class IngestReport:
    slides_read: int
    passages: int
    duplicates_removed: int = 0
    footers_removed: dict[str, list[str]] = field(default_factory=dict)
    near_empty: list[tuple[str, int]] = field(default_factory=list)  # (Lecture, Slide)


@dataclass(frozen=True)
class _Page:
    number: int
    lines: list[str]  # cleaned of broken glyphs and page numbers; no empty lines
    margin_lines: set[str]  # lines sitting in the top or bottom margin of the page
    spans: list[tuple[float, str]]  # (font size, cleaned text), for title detection

    def title(self, footers: set[str]) -> str:
        """The text set in the largest font, ignoring footers and the page number."""
        candidates = [
            (size, text)
            for size, text in self.spans
            if text and text not in footers and text != str(self.number)
        ]
        return max(candidates, key=lambda c: c[0])[1] if candidates else ""


@dataclass(frozen=True)
class _LectureRead:
    slides: list[Slide]  # Duplicate Slides already removed
    pages_read: int
    duplicates_removed: int
    footers: list[str]


def read_lecture(pdf_path: Path, cleaning: CleaningSettings) -> _LectureRead:
    """Read one Lecture: clean its Slides, then drop Duplicate Slides within it."""
    lecture = pdf_path.stem
    with pymupdf.open(pdf_path) as doc:
        pages = [
            _read_page(number, page, cleaning.footer_margin)
            for number, page in enumerate(doc, start=1)
        ]

    footers = _deck_footers(pages, cleaning)
    slides = [
        Slide(
            lecture,
            p.number,
            p.title(footers),
            "\n".join(line for line in p.lines if line not in footers),
        )
        for p in pages
    ]
    kept = [s for s, nxt in zip(slides, slides[1:] + [None]) if not _is_build_step(s, nxt)]
    return _LectureRead(kept, len(pages), len(slides) - len(kept), sorted(footers))


def _is_near_empty(slide: Slide, cleaning: CleaningSettings) -> bool:
    body = "".join(line for line in slide.text.splitlines() if line != slide.title)
    return len("".join(body.split())) < cleaning.near_empty_chars


def _is_build_step(slide: Slide, next_slide: Slide | None) -> bool:
    """A Slide is a Duplicate when the next Slide repeats it with more content (a build)."""
    return (
        next_slide is not None
        and bool(slide.title or slide.text)  # image-only Slides differ in what we can't see
        and slide.title == next_slide.title
        and set(slide.text.splitlines()) <= set(next_slide.text.splitlines())
    )


def _read_page(number: int, page: pymupdf.Page, margin: float) -> _Page:
    height = page.rect.height or 1.0
    lines: list[str] = []
    margin_lines: set[str] = set()
    spans: list[tuple[float, str]] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans.extend((s["size"], _clean_line(s["text"])) for s in line["spans"])
            text = _clean_line("".join(s["text"] for s in line["spans"]))
            if not text or text == str(number):
                continue
            lines.append(text)
            middle = (line["bbox"][1] + line["bbox"][3]) / 2 / height
            if middle < margin or middle > 1 - margin:
                margin_lines.add(text)
    return _Page(number, lines, margin_lines, spans)


def _deck_footers(pages: list[_Page], cleaning: CleaningSettings) -> set[str]:
    """Margin lines repeated on enough of a Lecture's Slides to be footers, not content."""
    counts = Counter(line for p in pages for line in p.margin_lines)
    needed = max(cleaning.footer_min_count, cleaning.footer_min_share * len(pages))
    return {line for line, count in counts.items() if count >= needed}


def _clean_line(line: str) -> str:
    line = _BROKEN_GLYPHS.sub("", line).strip()
    return "" if _SYMBOLS_ONLY.fullmatch(line) else line


def build_passages(slides: list[Slide]) -> list[Passage]:
    """Baseline: one Slide per Passage, prefixed with its Lecture and Slide titles."""
    return [
        Passage(
            lecture=s.lecture,
            slide=s.number,
            text=f"{s.lecture} | {s.title}\n{s.text}",
        )
        for s in slides
    ]


def ingest(
    lectures_dir: Path, index_dir: Path, config: RetrievalConfig, embedder: Embedder
) -> IngestReport:
    slides: list[Slide] = []
    pages_read = duplicates_removed = 0
    footers_removed: dict[str, list[str]] = {}
    for pdf in sorted(Path(lectures_dir).rglob("*.pdf")):
        lecture = read_lecture(pdf, config.cleaning)
        slides.extend(lecture.slides)
        pages_read += lecture.pages_read
        duplicates_removed += lecture.duplicates_removed
        if lecture.footers:
            footers_removed[pdf.stem] = lecture.footers
    near_empty = [(s.lecture, s.number) for s in slides if _is_near_empty(s, config.cleaning)]
    passages = build_passages(slides)

    vectors = embedder.embed([p.text for p in passages])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / DENSE_INDEX_FILE))
    (index_dir / PASSAGES_FILE).write_text(
        json.dumps([p.model_dump() for p in passages], ensure_ascii=False), encoding="utf-8"
    )
    return IngestReport(
        slides_read=pages_read,
        duplicates_removed=duplicates_removed,
        passages=len(passages),
        footers_removed=footers_removed,
        near_empty=near_empty,
    )
