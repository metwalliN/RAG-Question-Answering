"""Seam A: planning which Slides each drafted question targets, and checking drafts."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from conftest import make_lecture
from course_qa.config import RetrievalConfig
from course_qa.drafting import check_drafts, plan_drafts
from course_qa.ingest import ingest
from fakes import FakeEmbedder

TOPICS = [
    ("Fitts Law", "Movement time depends on distance and target width"),
    ("Hick Law", "Decision time grows with the number of choices"),
    ("GOMS", "Goals operators methods and selection rules"),
    ("Keystroke model", "Operators K P H M with fixed unit times"),
    ("Feedback", "Tell users their action succeeded"),
    ("Mental models", "Users predict behaviour from their own model"),
]


@pytest.fixture
def index(lectures_dir, index_dir):
    image_only = ("", "")
    make_lecture(lectures_dir / "Lecture 3 GOMS.pdf", TOPICS[:3] + [image_only] + TOPICS[3:])
    make_lecture(
        lectures_dir / "Lecture 4 Vision.pdf",
        [
            ("Colour perception", "Cones detect red green and blue light"),
            ("Rods", "Rods detect dim light and motion at night"),
            ("Fovea", "The fovea gives the sharpest central vision"),
        ],
    )
    ingest(lectures_dir, index_dir, RetrievalConfig(name="baseline"), FakeEmbedder())
    return index_dir


def test_targets_are_spread_by_lecture_size_and_skip_near_empty_slides(index):
    # Eligible Slides: 6 in Lecture 3 (its image-only Slide 4 is near-empty), 3 in Lecture 4.
    plan = plan_drafts(index, count=3, span_share=0.0, seed=1)

    assert Counter(t.slides[0].lecture for t in plan) == {"Lecture 3 GOMS": 2, "Lecture 4 Vision": 1}
    assert ("Lecture 3 GOMS", 4) not in {(s.lecture, s.slide) for t in plan for s in t.slides}


def test_a_share_of_targets_span_two_neighbouring_slides(index):
    plan = plan_drafts(index, count=5, span_share=0.4, seed=1)

    spans = [t for t in plan if t.kind == "span"]
    assert len(spans) == 2
    for t in spans:
        first, second = t.slides
        assert first.lecture == second.lecture
        assert second.slide == first.slide + 1


def test_no_slide_is_targeted_twice_and_the_plan_is_reproducible(index):
    plan = plan_drafts(index, count=8, span_share=0.25, seed=7)

    used = [(s.lecture, s.slide) for t in plan for s in t.slides]
    assert len(used) == len(set(used))
    assert plan == plan_drafts(index, count=8, span_share=0.25, seed=7)


def write_drafts(path, drafts):
    path.write_text("\n".join(json.dumps(d) for d in drafts), encoding="utf-8")
    return path


def draft(did, question, gold, kind="single"):
    return {
        "id": did,
        "target_id": "t001",
        "kind": kind,
        "question": question,
        "reference_answer": "…",
        "gold_slides": [{"lecture": lecture, "slide": slide} for lecture, slide in gold],
    }


def test_drafts_copying_slide_wording_are_flagged_and_paraphrases_are_not(index, tmp_path):
    drafts = write_drafts(tmp_path / "drafts.jsonl", [
        draft("d1", "Movement time depends on distance and target width?", [("Lecture 3 GOMS", 1)]),
        draft("d2", "How do the size of a button and how far away it is change pointing speed?",
              [("Lecture 3 GOMS", 1)]),
    ])

    checks = {c.draft_id: c for c in check_drafts(drafts, index)}

    assert checks["d1"].copies_wording and checks["d1"].longest_shared_run >= 5
    assert not checks["d2"].copies_wording


def test_a_draft_citing_a_slide_outside_the_ingest_is_reported(index, tmp_path):
    drafts = write_drafts(tmp_path / "drafts.jsonl", [
        draft("d1", "What do rods detect?", [("Lecture 4 Vision", 2), ("Lecture 4 Vision", 99)]),
        draft("d2", "What does the image-only slide show?", [("Lecture 3 GOMS", 4)]),  # near-empty
    ])

    checks = {c.draft_id: c for c in check_drafts(drafts, index)}

    assert checks["d1"].unknown_gold_slides == [("Lecture 4 Vision", 99)]
    assert checks["d2"].unknown_gold_slides == []  # near-empty Slides still exist in the ingest
