"""Ingest: turn Lecture PDFs into Slides, Passages and a searchable index."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import pymupdf

from course_qa.config import RetrievalConfig
from course_qa.models import Embedder
from course_qa.passages import Passage

PASSAGES_FILE = "passages.json"
DENSE_INDEX_FILE = "dense.faiss"


@dataclass(frozen=True)
class Slide:
    lecture: str
    number: int  # 1-based, as students see it
    title: str
    text: str


@dataclass(frozen=True)
class IngestReport:
    slides_read: int
    passages: int


def read_slides(pdf_path: Path) -> list[Slide]:
    lecture = pdf_path.stem
    slides = []
    with pymupdf.open(pdf_path) as doc:
        for number, page in enumerate(doc, start=1):
            slides.append(
                Slide(lecture, number, _slide_title(page), page.get_text().strip())
            )
    return slides


def _slide_title(page: pymupdf.Page) -> str:
    """The text set in the largest font on the page."""
    best_size, best_text = 0.0, ""
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip()
                if text and span["size"] > best_size:
                    best_size, best_text = span["size"], text
    return best_text


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
    slides = [s for pdf in sorted(Path(lectures_dir).rglob("*.pdf")) for s in read_slides(pdf)]
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
    return IngestReport(slides_read=len(slides), passages=len(passages))
