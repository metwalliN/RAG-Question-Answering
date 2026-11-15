"""Planning the Evaluation Set drafts: which Slides each candidate question targets.

The questions themselves are written in-session by the coding assistant (ADR-0002);
this module decides what they are about, so coverage is spread fairly and reproducibly.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from course_qa.evaluation_set import GoldSlide
from course_qa.ingest import SLIDES_FILE

# A question sharing this many consecutive words with its Slide copies the Slide's wording.
COPIED_RUN = 5


@dataclass(frozen=True)
class TargetSlide:
    lecture: str
    slide: int
    title: str
    text: str


@dataclass(frozen=True)
class DraftTarget:
    id: str
    kind: str  # "single", or "span" for two neighbouring Slides whose answer needs both
    slides: list[TargetSlide]


def plan_drafts(index_dir: Path, count: int, span_share: float, seed: int) -> list[DraftTarget]:
    """Spread ``count`` targets across Lectures in proportion to their eligible Slides."""
    rng = random.Random(seed)
    eligible = _eligible_slides_by_lecture(index_dir)
    targets: list[DraftTarget] = []
    for lecture, quota in _allocate(count, {lec: len(s) for lec, s in eligible.items()}).items():
        slides = eligible[lecture]
        spans = round(quota * span_share)
        while spans and 2 * spans + (quota - spans) > len(slides):
            spans -= 1  # a small Lecture can't fit every span; ask single-Slide questions instead
        pairs = _neighbouring_pairs(slides, spans, rng)
        used = {s.slide for pair in pairs for s in pair}
        singles = rng.sample([s for s in slides if s.slide not in used], quota - len(pairs))
        for group in [list(pair) for pair in pairs] + [[s] for s in singles]:
            kind = "span" if len(group) == 2 else "single"
            targets.append(DraftTarget(f"t{len(targets) + 1:03d}", kind, group))
    return targets


def _neighbouring_pairs(
    slides: list[TargetSlide], wanted: int, rng: random.Random
) -> list[tuple[TargetSlide, TargetSlide]]:
    """Up to ``wanted`` non-overlapping pairs of consecutive Slides (page n and n + 1)."""
    by_number = {s.slide: s for s in slides}
    candidates = [(s, by_number[s.slide + 1]) for s in slides if s.slide + 1 in by_number]
    rng.shuffle(candidates)
    chosen: list[tuple[TargetSlide, TargetSlide]] = []
    taken: set[int] = set()
    for first, second in candidates:
        if len(chosen) == wanted:
            break
        if first.slide not in taken and second.slide not in taken:
            chosen.append((first, second))
            taken |= {first.slide, second.slide}
    return chosen


class Draft(BaseModel):
    """A candidate Evaluation Pair written in-session, before the developer's review."""

    id: str
    target_id: str
    kind: str  # "single", "span", or "unanswerable"
    question: str
    reference_answer: str
    gold_slides: list[GoldSlide]  # empty for a drafted Unanswerable Question
    unanswerable: bool = False


@dataclass(frozen=True)
class DraftCheck:
    draft_id: str
    longest_shared_run: int  # most consecutive words the question shares with its Slides
    copies_wording: bool
    unknown_gold_slides: list[tuple[str, int]]


def load_drafts(path: Path) -> list[Draft]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Draft.model_validate_json(line) for line in lines if line.strip()]


def check_drafts(drafts_path: Path, index_dir: Path) -> list[DraftCheck]:
    """Flag drafts that copy their Slides' wording or cite Slides outside the ingest."""
    slides = json.loads((Path(index_dir) / SLIDES_FILE).read_text(encoding="utf-8"))
    text_of = {(s["lecture"], s["slide"]): s["text"] for s in slides}
    checks = []
    for d in load_drafts(drafts_path):
        refs = [(g.lecture, g.slide) for g in d.gold_slides]
        known = [r for r in refs if r in text_of]
        run = max((_longest_shared_run(d.question, text_of[r]) for r in known), default=0)
        checks.append(
            DraftCheck(d.id, run, run >= COPIED_RUN, [r for r in refs if r not in text_of])
        )
    return checks


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _longest_shared_run(question: str, slide_text: str) -> int:
    """Length of the longest run of consecutive words appearing in both texts."""
    q, s = _words(question), _words(slide_text)
    best, previous = 0, [0] * (len(s) + 1)
    for qw in q:
        current = [0] * (len(s) + 1)
        for j, sw in enumerate(s, start=1):
            if qw == sw:
                current[j] = previous[j - 1] + 1
                best = max(best, current[j])
        previous = current
    return best


def _eligible_slides_by_lecture(index_dir: Path) -> dict[str, list[TargetSlide]]:
    slides = json.loads((Path(index_dir) / SLIDES_FILE).read_text(encoding="utf-8"))
    by_lecture: dict[str, list[TargetSlide]] = defaultdict(list)
    for s in slides:
        if not s["near_empty"]:
            by_lecture[s["lecture"]].append(TargetSlide(s["lecture"], s["slide"], s["title"], s["text"]))
    return dict(by_lecture)


def _allocate(count: int, sizes: dict[str, int]) -> dict[str, int]:
    """Largest-remainder split of ``count`` in proportion to ``sizes``."""
    total = sum(sizes.values())
    exact = {lec: count * n / total for lec, n in sizes.items()}
    quotas = {lec: int(x) for lec, x in exact.items()}
    by_remainder = sorted(sizes, key=lambda lec: exact[lec] - quotas[lec], reverse=True)
    for lec in by_remainder[: count - sum(quotas.values())]:
        quotas[lec] += 1
    return quotas
