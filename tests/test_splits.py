"""Seam C: the fixed-seed Dev/Test split and the whole-file validation (pure functions)."""

from __future__ import annotations

import json
import random

from course_qa.evaluation_set import GoldSlide, ReviewedPair, assign_splits, validate_evaluation_set

SLIDES = {("L04 Vision", n) for n in range(1, 200)}


def pairs(answerable: int, unanswerable: int) -> list[ReviewedPair]:
    made = [
        ReviewedPair(id=f"d{i:03d}", question=f"q{i}", reference_answer="a",
                     gold_slides=[GoldSlide(lecture="L04 Vision", slide=i + 1)],
                     unanswerable=False, origin="drafted-and-reviewed")
        for i in range(answerable)
    ]
    made += [
        ReviewedPair(id=f"h{i:03d}", question=f"u{i}", reference_answer="Not covered.",
                     gold_slides=[], unanswerable=True, origin="hand-written")
        for i in range(unanswerable)
    ]
    return made


def test_the_split_is_100_50_with_unanswerable_questions_in_both_and_is_reproducible():
    reviewed = pairs(answerable=135, unanswerable=15)
    shuffled = random.Random(3).sample(reviewed, len(reviewed))

    split = assign_splits(reviewed, seed=2026)

    dev = [p for p in split if p.split == "dev"]
    test = [p for p in split if p.split == "test"]
    assert (len(dev), len(test)) == (100, 50)
    assert (sum(p.unanswerable for p in dev), sum(p.unanswerable for p in test)) == (10, 5)
    assert split == assign_splits(shuffled, seed=2026)  # review order doesn't matter


def evaluation_file(tmp_path, rows):
    path = tmp_path / "evaluation_set.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


def test_a_clean_evaluation_set_has_no_problems(tmp_path):
    rows = [p.model_dump() for p in assign_splits(pairs(135, 15), seed=2026)]

    assert validate_evaluation_set(evaluation_file(tmp_path, rows), SLIDES) == []


def test_validation_reports_unknown_slides_duplicates_and_wrong_split_sizes(tmp_path):
    rows = [p.model_dump() for p in assign_splits(pairs(135, 15), seed=2026)]
    rows[0]["gold_slides"] = [{"lecture": "L09 Nothing", "slide": 1}]
    rows[1]["id"] = rows[2]["id"]
    next(r for r in rows if r["split"] == "test")["split"] = "dev"  # now 101 dev / 49 test

    problems = validate_evaluation_set(evaluation_file(tmp_path, rows), SLIDES)

    assert any("L09 Nothing" in p for p in problems)
    assert any("duplicate" in p and rows[2]["id"] in p for p in problems)
    assert any("split sizes" in p for p in problems)


def test_validation_reports_a_split_without_unanswerable_questions(tmp_path):
    rows = [p.model_dump() for p in assign_splits(pairs(135, 15), seed=2026)]
    for r in rows:
        if r["unanswerable"]:
            r["split"] = "dev"

    problems = validate_evaluation_set(evaluation_file(tmp_path, rows), SLIDES)

    assert any("Test Split has no Unanswerable" in p for p in problems)


def test_a_larger_set_is_split_two_thirds_to_one_third():
    split = assign_splits(pairs(answerable=197, unanswerable=30), seed=2026)

    dev = [p for p in split if p.split == "dev"]
    test = [p for p in split if p.split == "test"]
    assert (len(dev), len(test)) == (151, 76)
    assert (sum(p.unanswerable for p in dev), sum(p.unanswerable for p in test)) == (20, 10)
