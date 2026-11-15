"""Seam B: the review session behind the Evaluation Set review page."""

from __future__ import annotations

import json

import pytest

from conftest import make_lecture
from course_qa.config import RetrievalConfig
from course_qa.ingest import ingest
from course_qa.review import ReviewSession
from course_qa.slide_images import UnknownSlide
from fakes import FakeEmbedder

V = "Lecture 4 Vision"


@pytest.fixture
def index(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / f"{V}.pdf",
        [
            ("Colour perception", "Cones detect red green and blue light"),
            ("Rods", "Rods detect dim light and motion at night"),
            ("Fovea", "The fovea gives the sharpest central vision"),
        ],
    )
    ingest(lectures_dir, index_dir, RetrievalConfig(name="baseline"), FakeEmbedder())
    return index_dir


@pytest.fixture
def drafts(tmp_path):
    rows = [
        {"id": "d001", "target_id": "t001", "kind": "single", "question": "What do cones sense?",
         "reference_answer": "Colour.", "gold_slides": [{"lecture": V, "slide": 1}]},
        {"id": "d002", "target_id": "t002", "kind": "single", "question": "What are rods good at?",
         "reference_answer": "Dim light.", "gold_slides": [{"lecture": V, "slide": 2}]},
        {"id": "d003", "target_id": "t003", "kind": "single", "question": "Where is vision sharpest?",
         "reference_answer": "The fovea.", "gold_slides": [{"lecture": V, "slide": 3}]},
    ]
    path = tmp_path / "drafts.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


def session(drafts, index, tmp_path):
    return ReviewSession(drafts, index, reviewed=tmp_path / "reviewed.jsonl")


def reviewed_pairs(tmp_path):
    lines = (tmp_path / "reviewed.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_accepting_a_draft_saves_it_and_a_new_session_resumes_at_the_next_one(drafts, index, tmp_path):
    first = session(drafts, index, tmp_path)
    first.accept(first.next_draft().id)

    resumed = session(drafts, index, tmp_path)

    assert resumed.next_draft().id == "d002"
    [saved] = reviewed_pairs(tmp_path)
    assert (saved["draft_id"], saved["decision"]) == ("d001", "accepted")
    assert saved["pair"]["question"] == "What do cones sense?"
    assert saved["pair"]["origin"] == "drafted-and-reviewed"


def test_editing_a_draft_saves_the_new_wording_and_extra_gold_slides(drafts, index, tmp_path):
    review = session(drafts, index, tmp_path)

    review.edit(
        "d001",
        question="Which receptors let us see colour?",
        gold_slides=[(V, 1), (V, 3)],
    )

    [saved] = reviewed_pairs(tmp_path)
    assert saved["decision"] == "edited"
    assert saved["pair"]["question"] == "Which receptors let us see colour?"
    assert saved["pair"]["reference_answer"] == "Colour."  # untouched fields are kept
    assert [(g["lecture"], g["slide"]) for g in saved["pair"]["gold_slides"]] == [(V, 1), (V, 3)]


def test_a_gold_slide_outside_the_ingest_is_rejected_and_nothing_is_saved(drafts, index, tmp_path):
    review = session(drafts, index, tmp_path)

    with pytest.raises(UnknownSlide):
        review.edit("d001", gold_slides=[(V, 1), (V, 99)])

    assert not (tmp_path / "reviewed.jsonl").exists()
    assert review.next_draft().id == "d001"


def test_rejected_drafts_are_dropped_and_a_later_decision_overrides_an_earlier_one(drafts, index, tmp_path):
    review = session(drafts, index, tmp_path)
    review.reject("d001", reason="too easy")
    review.reject("d002", reason="ambiguous")
    review.accept("d002")  # changed my mind

    resumed = session(drafts, index, tmp_path)

    assert resumed.next_draft().id == "d003"
    assert [p.id for p in resumed.kept_pairs()] == ["d002"]
    assert resumed.progress() == (2, 3)


def test_hand_written_and_unanswerable_pairs_are_saved_in_the_same_format(drafts, index, tmp_path):
    review = session(drafts, index, tmp_path)

    review.add_hand_written("How do rods and cones divide up the work?", "Rods: dim light. Cones: colour.",
                            gold_slides=[(V, 1), (V, 2)])
    review.add_hand_written("When is the exam?", "The Course Material doesn't say.",
                            gold_slides=[], unanswerable=True)

    kept = session(drafts, index, tmp_path).kept_pairs()
    assert [(p.id, p.origin, p.unanswerable, len(p.gold_slides)) for p in kept] == [
        ("h001", "hand-written", False, 2),
        ("h002", "hand-written", True, 0),
    ]


def test_a_decision_records_a_note_saying_who_made_it(drafts, index, tmp_path):
    review = session(drafts, index, tmp_path)

    review.accept("d001", note="Claude Code second pass: ok")
    review.edit("d002", question="What do rods let us do?", note="Claude Code second pass: fixed")

    assert [r["reason"] for r in reviewed_pairs(tmp_path)] == [
        "Claude Code second pass: ok",
        "Claude Code second pass: fixed",
    ]


@pytest.fixture
def unanswerable_drafts(tmp_path):
    rows = [
        {"id": "u001", "target_id": "unanswerable", "kind": "unanswerable", "unanswerable": True,
         "question": "When is the final exam?", "reference_answer": "The Course Material doesn't say.",
         "gold_slides": []},
        {"id": "u002", "target_id": "unanswerable", "kind": "unanswerable", "unanswerable": True,
         "question": "Which cones see ultraviolet?", "reference_answer": "The Course Material doesn't say.",
         "gold_slides": []},
    ]
    path = tmp_path / "unanswerable.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


def test_a_drafted_unanswerable_question_is_kept_without_gold_slides(unanswerable_drafts, index, tmp_path):
    review = session(unanswerable_drafts, index, tmp_path)

    review.accept("u001")
    review.edit("u002", gold_slides=[(V, 1)])  # the reviewer found a Slide that does answer it

    kept = {p.id: p for p in session(unanswerable_drafts, index, tmp_path).kept_pairs()}
    assert (kept["u001"].unanswerable, kept["u001"].gold_slides) == (True, [])
    assert kept["u002"].unanswerable is False
    assert [(g.lecture, g.slide) for g in kept["u002"].gold_slides] == [(V, 1)]
