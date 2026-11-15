"""Ingest: turn Lecture PDFs into Slides, Passages and a searchable index."""

from __future__ import annotations

import json
import re
import unicodedata
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
SLIDES_FILE = "slides.json"  # Slide-level data for planning, review and Slide images

# Symbol-font bullets extract as the replacement character or private-use code points;
# equation fonts draw hat accents (as in "ŷ") with Sinhala signs, which English decks never use.
_BROKEN_GLYPHS = re.compile("[�-඀-෿]")
# Equations extract as "mathematical" letters and digits (𝜽𝟎); fold them to plain ones (θ0).
_MATH_ALPHANUMERIC = re.compile("[\U0001d400-\U0001d7ff]")
# Lines whose font is within this many points of the largest belong to the title.
_TITLE_SIZE_TOLERANCE = 0.5
# A wrapped title's next line starts within this many line-heights of the one above
# (about 1.1 in the real decks); a new paragraph in the same font starts 1.9 or more below.
_TITLE_WRAP_GAP = 1.5
_LIST_ITEM = re.compile(r"^([•·▪◦❖►➢✓–—*-]|\d+[.)]\s)")
# Sub-bullets set in Courier extract as a lowercase "o" before the text.
_O_BULLET = re.compile(r"^o(\s+|$)")
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
    sized_lines: list[tuple[float, float, str]]  # (largest font size, top y, text), reading order

    def title(self, footers: set[str]) -> str:
        """The first line set in the largest font, joined with the lines it wraps onto.

        A following line continues the title only if it is in the same font size, sits on
        the same baseline or within ``_TITLE_WRAP_GAP`` line-heights of the line above, and
        is not a list item. Body text that merely shares the title's size starts a new
        paragraph (a bigger gap) or a bullet, so it is left out. Footers and the page
        number are never part of a title.
        """
        candidates = [line for line in self.sized_lines if line[2] not in footers]
        if not candidates:
            return ""
        largest = max(size for size, _, _ in candidates)
        start = next(i for i, (size, _, _) in enumerate(candidates) if size >= largest - _TITLE_SIZE_TOLERANCE)
        title = [candidates[start]]
        for size, top, text in candidates[start + 1:]:
            _, prev_top, _ = title[-1]
            wraps = 0 <= top - prev_top <= _TITLE_WRAP_GAP * size
            if abs(size - largest) > _TITLE_SIZE_TOLERANCE or not wraps or _LIST_ITEM.match(text):
                break
            title.append((size, top, text))
        return " ".join(text for _, _, text in title)


@dataclass(frozen=True)
class _LectureRead:
    slides: list[Slide]  # Duplicate Slides already removed
    pages_read: int
    duplicates_removed: int
    footers: list[str]


def read_lecture(pdf_path: Path, cleaning: CleaningSettings) -> _LectureRead:
    """Read one Lecture: clean its Slides, then drop Duplicate Slides within it."""
    lecture = lecture_name(pdf_path)
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


def lecture_name(pdf_path: Path) -> str:
    """The Lecture's display name, as Citations show it: "L04_Vision.pdf" → "L04 Vision"."""
    return pdf_path.stem.replace("_", " ")


def _is_near_empty(slide: Slide, cleaning: CleaningSettings) -> bool:
    # A wrapped title's lines ("Supervised", "Learning") are part of the title, not body.
    body = "".join(line for line in slide.text.splitlines() if line not in slide.title)
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
    sized_lines: list[tuple[float, str]] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = _clean_line("".join(s["text"] for s in line["spans"]))
            if not text or text == str(number):
                continue
            lines.append(text)
            sized_lines.append((max(s["size"] for s in line["spans"]), line["bbox"][1], text))
            middle = (line["bbox"][1] + line["bbox"][3]) / 2 / height
            if middle < margin or middle > 1 - margin:
                margin_lines.add(text)
    return _Page(number, lines, margin_lines, sized_lines)


def _deck_footers(pages: list[_Page], cleaning: CleaningSettings) -> set[str]:
    """Margin lines repeated on enough of a Lecture's Slides to be footers, not content."""
    counts = Counter(line for p in pages for line in p.margin_lines)
    needed = max(cleaning.footer_min_count, cleaning.footer_min_share * len(pages))
    return {line for line, count in counts.items() if count >= needed}


def _clean_line(line: str) -> str:
    line = _BROKEN_GLYPHS.sub("", line)
    line = _MATH_ALPHANUMERIC.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), line)
    line = _O_BULLET.sub("", line.strip())
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
    lectures_dir = Path(lectures_dir)
    slides: list[Slide] = []
    pages_read = duplicates_removed = 0
    footers_removed: dict[str, list[str]] = {}
    for pdf in sorted(Path(lectures_dir).rglob("*.pdf")):
        lecture = read_lecture(pdf, config.cleaning)
        slides.extend(lecture.slides)
        pages_read += lecture.pages_read
        duplicates_removed += lecture.duplicates_removed
        if lecture.footers:
            footers_removed[lecture_name(pdf)] = lecture.footers
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
    near_empty_set = set(near_empty)
    sources = {
        lecture_name(pdf): pdf.relative_to(lectures_dir).as_posix()
        for pdf in Path(lectures_dir).rglob("*.pdf")
    }
    (index_dir / SLIDES_FILE).write_text(
        json.dumps(
            [
                {
                    "lecture": s.lecture,
                    "slide": s.number,
                    "title": s.title,
                    "text": s.text,
                    "near_empty": (s.lecture, s.number) in near_empty_set,
                    "source": sources[s.lecture],  # the PDF, relative to the lectures folder
                }
                for s in slides
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return IngestReport(
        slides_read=pages_read,
        duplicates_removed=duplicates_removed,
        passages=len(passages),
        footers_removed=footers_removed,
        near_empty=near_empty,
    )
