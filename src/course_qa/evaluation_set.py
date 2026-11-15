"""The Evaluation Set: a versioned JSONL file of Evaluation Pairs."""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError, model_validator

Split = Literal["dev", "test"]


class InvalidEvaluationSet(Exception):
    """The Evaluation Set file has a pair that would corrupt the metrics."""


class GoldSlide(BaseModel):
    lecture: str
    slide: int


class ReviewedPair(BaseModel):
    """An Evaluation Pair before it is assigned to the Dev or Test Split."""

    id: str
    question: str
    reference_answer: str
    gold_slides: list[GoldSlide]  # empty only for an Unanswerable Question
    unanswerable: bool
    # "sample": unreviewed smoke-check pairs for building the machinery; never reported.
    origin: Literal["drafted-and-reviewed", "hand-written", "sample"]

    @model_validator(mode="after")
    def _gold_slides_match_answerability(self) -> "ReviewedPair":
        if self.unanswerable and self.gold_slides:
            raise ValueError("an Unanswerable Question can't have Gold Slides")
        if not self.unanswerable and not self.gold_slides:
            raise ValueError("an answerable question needs at least one Gold Slide")
        return self


class EvaluationPair(ReviewedPair):
    split: Split


def load_evaluation_set(path: Path) -> list[EvaluationPair]:
    pairs = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            pairs.append(EvaluationPair.model_validate_json(line))
        except ValidationError as exc:
            pair_id = _pair_id(line)
            reasons = "; ".join(e["msg"] for e in exc.errors())
            raise InvalidEvaluationSet(f"line {number} (pair {pair_id}): {reasons}") from exc
    return pairs


TEST_SHARE = 1 / 3  # the Test Split's share of the Evaluation Set; the Dev Split gets the rest


def test_split_size(total: int, test_share: float = TEST_SHARE) -> int:
    return round(total * test_share)


def assign_splits(pairs: list[ReviewedPair], seed: int, test_share: float = TEST_SHARE) -> list[EvaluationPair]:
    """Split once, with a fixed seed, stratified so both splits get Unanswerable Questions.

    Pairs are sorted by id first, so the result doesn't depend on review order.
    """
    rng = random.Random(seed)
    ordered = sorted(pairs, key=lambda p: p.id)
    test_size = test_split_size(len(ordered), test_share)
    unanswerable = [p for p in ordered if p.unanswerable]
    answerable = [p for p in ordered if not p.unanswerable]
    test_unanswerable = round(test_size * len(unanswerable) / len(ordered)) if ordered else 0
    test_ids = {p.id for p in rng.sample(unanswerable, test_unanswerable)}
    test_ids |= {p.id for p in rng.sample(answerable, test_size - test_unanswerable)}
    return [
        EvaluationPair(**p.model_dump(), split="test" if p.id in test_ids else "dev")
        for p in ordered
    ]


def validate_evaluation_set(
    path: Path,
    known_slides: set[tuple[str, int]],
    test_share: float = TEST_SHARE,
) -> list[str]:
    """Every problem with the Evaluation Set file, as readable messages; [] when clean."""
    try:
        pairs = load_evaluation_set(path)
    except InvalidEvaluationSet as exc:
        return [str(exc)]
    problems = []
    for pid, count in Counter(p.id for p in pairs).items():
        if count > 1:
            problems.append(f"duplicate pair id {pid} ({count} times)")
    for p in pairs:
        unknown = [(g.lecture, g.slide) for g in p.gold_slides if (g.lecture, g.slide) not in known_slides]
        if unknown:
            problems.append(f"pair {p.id}: Gold Slides not in the current ingest: {unknown}")
    sizes = Counter(p.split for p in pairs)
    test_size = test_split_size(len(pairs), test_share)
    if (sizes["dev"], sizes["test"]) != (len(pairs) - test_size, test_size):
        problems.append(
            f"split sizes are {sizes['dev']} dev / {sizes['test']} test, "
            f"expected {len(pairs) - test_size} / {test_size}"
        )
    for split, name in (("dev", "Dev"), ("test", "Test")):
        if not any(p.unanswerable for p in pairs if p.split == split):
            problems.append(f"the {name} Split has no Unanswerable Questions")
    return problems


def _pair_id(line: str) -> str:
    try:
        return str(json.loads(line).get("id", "?"))
    except (json.JSONDecodeError, AttributeError):
        return "?"
