"""Seam 2: the pure scoring function (ADR-0001 rules), on hand-made rankings."""

from __future__ import annotations

import pytest

from course_qa.scoring import PairOutcome, score


def slides(*numbers: int, lecture: str = "L1") -> list[tuple[str, int]]:
    """Anchor Slides of ranked Passages, best first."""
    return [(lecture, n) for n in numbers]


def answerable(ranked, gold, refused=False) -> PairOutcome:
    return PairOutcome(ranked_slides=ranked, gold_slides=set(gold), unanswerable=False, refused=refused)


def unanswerable(refused: bool) -> PairOutcome:
    return PairOutcome(ranked_slides=slides(1, 2, 3), gold_slides=set(), unanswerable=True, refused=refused)


def test_a_gold_slide_counts_only_within_the_top_five():
    hit_at_5 = answerable(slides(1, 2, 3, 4, 9), gold=slides(9))
    miss_at_6 = answerable(slides(1, 2, 3, 4, 5, 9), gold=slides(9))

    assert score([hit_at_5, miss_at_6]).recall_at_5 == 0.5


def test_passages_are_collapsed_to_distinct_anchor_slides_before_the_top_five():
    # Five Passages split from Slide 1, then the Gold Slide: collapsed, that's rank 2.
    outcome = answerable(slides(1, 1, 1, 1, 1, 9), gold=slides(9))

    assert score([outcome]).recall_at_5 == 1.0


def test_mrr_uses_the_first_gold_slide_rank_after_collapsing():
    # Collapsed: [1, 7, 3, 9]; Gold Slides 3 and 9; the first one is at rank 3.
    two_golds = answerable(slides(1, 1, 7, 3, 9), gold=slides(9, 3))
    first_place = answerable(slides(4, 5), gold=slides(4))
    miss = answerable(slides(1, 2, 3, 4, 5, 6), gold=slides(6))

    assert score([two_golds, first_place, miss]).mrr == pytest.approx((1 / 3 + 1 + 0) / 3)


def test_unanswerable_questions_score_refusals_and_stay_out_of_retrieval_metrics():
    outcomes = [
        answerable(slides(9), gold=slides(9)),
        answerable(slides(9), gold=slides(9), refused=True),  # a False Refusal
        unanswerable(refused=True),
        unanswerable(refused=False),
        unanswerable(refused=True),
    ]

    scores = score(outcomes)

    assert (scores.recall_at_5, scores.mrr) == (1.0, 1.0)  # no Gold Slide to miss
    assert scores.refusal_accuracy == pytest.approx(2 / 3)
    assert scores.false_refusal_rate == 0.5


def test_a_metric_with_nothing_to_measure_is_none_not_zero():
    only_answerable = score([answerable(slides(9), gold=slides(9))])
    only_unanswerable = score([unanswerable(refused=True)])

    assert only_answerable.refusal_accuracy is None
    assert (only_unanswerable.recall_at_5, only_unanswerable.mrr) == (None, None)
    assert only_unanswerable.false_refusal_rate is None
