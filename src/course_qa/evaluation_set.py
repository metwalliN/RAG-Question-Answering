"""The Evaluation Set: a versioned JSONL file of Evaluation Pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError, model_validator

Split = Literal["dev", "test"]


class InvalidEvaluationSet(Exception):
    """The Evaluation Set file has a pair that would corrupt the metrics."""


class GoldSlide(BaseModel):
    lecture: str
    slide: int


class EvaluationPair(BaseModel):
    id: str
    question: str
    reference_answer: str
    gold_slides: list[GoldSlide]  # empty only for an Unanswerable Question
    unanswerable: bool
    # "sample": unreviewed smoke-check pairs for building the machinery; never reported.
    origin: Literal["drafted-and-reviewed", "hand-written", "sample"]
    split: Split

    @model_validator(mode="after")
    def _gold_slides_match_answerability(self) -> "EvaluationPair":
        if self.unanswerable and self.gold_slides:
            raise ValueError("an Unanswerable Question can't have Gold Slides")
        if not self.unanswerable and not self.gold_slides:
            raise ValueError("an answerable question needs at least one Gold Slide")
        return self


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


def _pair_id(line: str) -> str:
    try:
        return str(json.loads(line).get("id", "?"))
    except (json.JSONDecodeError, AttributeError):
        return "?"
