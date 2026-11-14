"""Scoring: the pure function behind every reported number (ADR-0001)."""

from __future__ import annotations

from dataclasses import dataclass

AnchorSlide = tuple[str, int]  # (Lecture, Slide number)

K = 5


@dataclass(frozen=True)
class PairOutcome:
    """What the assistant did for one Evaluation Pair."""

    ranked_slides: list[AnchorSlide]  # Anchor Slides of the ranked Passages, best first
    gold_slides: set[AnchorSlide]
    unanswerable: bool
    refused: bool | None  # None when the run didn't ask the assistant to answer


@dataclass(frozen=True)
class Scores:
    recall_at_5: float | None
    mrr: float | None  # MRR@5: a Gold Slide beyond the top 5 counts as 0
    refusal_accuracy: float | None  # share of Unanswerable Questions refused
    false_refusal_rate: float | None  # share of answerable questions refused


def _reciprocal_rank(o: PairOutcome) -> float:
    for rank, slide in enumerate(top_slides(o.ranked_slides), start=1):
        if slide in o.gold_slides:
            return 1 / rank
    return 0.0


def top_slides(ranked: list[AnchorSlide], k: int = K) -> list[AnchorSlide]:
    """The first k distinct Anchor Slides, in rank order."""
    return list(dict.fromkeys(ranked))[:k]


def score(outcomes: list[PairOutcome]) -> Scores:
    answerable = [o for o in outcomes if not o.unanswerable]
    unanswerable = [o for o in outcomes if o.unanswerable]
    answered = all(o.refused is not None for o in outcomes)
    return Scores(
        recall_at_5=_mean([bool(set(top_slides(o.ranked_slides)) & o.gold_slides) for o in answerable]),
        mrr=_mean([_reciprocal_rank(o) for o in answerable]),
        refusal_accuracy=_mean([o.refused for o in unanswerable]) if answered else None,
        false_refusal_rate=_mean([o.refused for o in answerable]) if answered else None,
    )


def _mean(values: list[float]) -> float | None:
    """None when there is nothing to measure, rather than a misleading 0."""
    return sum(values) / len(values) if values else None
