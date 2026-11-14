"""Seam 1, ingest side: cleaning Slide text, Duplicate Slides, near-empty Slides."""

from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import BROKEN_BULLET, make_lecture
from course_qa.api import create_app
from course_qa.config import RetrievalConfig
from course_qa.ingest import ingest
from fakes import FakeEmbedder, ScriptedLLM

def ingest_and_ask(lectures_dir, index_dir, question, top_k=5):
    config = RetrievalConfig(name="baseline", top_k=top_k)
    embedder = FakeEmbedder()
    report = ingest(lectures_dir, index_dir, config, embedder)
    client = TestClient(create_app(index_dir, config, embedder, ScriptedLLM(answer="[1]")))
    return report, client.post("/ask", json={"question": question}).json()


def test_broken_bullet_glyphs_are_stripped_from_passages(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 4 Vision.pdf",
        [("Colour perception", f"{BROKEN_BULLET} Cones detect light\n{BROKEN_BULLET} Rods see dim light")],
    )

    _, body = ingest_and_ask(lectures_dir, index_dir, "What do cones detect?")

    passage = body["retrieval"][0]["passage"]
    assert "Cones detect light" in passage
    assert BROKEN_BULLET not in passage


def test_page_numbers_are_removed_but_other_numbers_are_kept(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf",
        [
            ("Welcome", "Course overview"),
            ("Lab capacity", "Seats in the usability lab\n42"),
        ],
        page_numbers=True,
    )

    _, body = ingest_and_ask(lectures_dir, index_dir, "How many seats in the usability lab?")

    top = body["retrieval"][0]
    assert top["slide"] == 2
    lines = top["passage"].splitlines()
    assert "42" in lines
    assert "2" not in lines


SIX_SLIDES = [
    ("Fitts Law", "Movement time depends on distance and target width"),
    ("Hick Law", "Decision time grows with the number of choices"),
    ("GOMS", "Goals operators methods and selection rules"),
    ("Keystroke model", "Operators K P H M with unit times"),
    ("Feedback", "Tell users their action succeeded"),
    ("Summary", "Review before the quiz"),
]


def test_repeated_deck_footers_are_removed_and_reported(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf", SIX_SLIDES, footer="Human Computer Interaction"
    )

    report, body = ingest_and_ask(lectures_dir, index_dir, "What does movement time depend on?")

    assert all("Human Computer Interaction" not in r["passage"] for r in body["retrieval"])
    assert report.footers_removed == {"Lecture 3 GOMS": ["Human Computer Interaction"]}


def test_a_line_on_too_few_slides_is_not_treated_as_a_footer(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf",
        SIX_SLIDES[:4],  # the footer appears on only 4 Slides, below the minimum of 5
        footer="Human Computer Interaction",
    )

    report, body = ingest_and_ask(lectures_dir, index_dir, "What does movement time depend on?")

    assert "Human Computer Interaction" in body["retrieval"][0]["passage"]
    assert report.footers_removed == {}


def test_a_footer_is_never_taken_as_a_slide_title(lectures_dir, index_dir):
    image_only_slide = ("", "")
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf",
        SIX_SLIDES + [image_only_slide],
        footer="Human Computer Interaction",
        page_numbers=True,
    )

    _, body = ingest_and_ask(lectures_dir, index_dir, "Lecture 3 GOMS", top_k=20)

    assert len(body["retrieval"]) == 7
    passages = {r["slide"]: r["passage"] for r in body["retrieval"]}
    assert all("Human Computer Interaction" not in p for p in passages.values())


def test_a_progressive_build_keeps_only_its_most_complete_slide(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf",
        [
            ("Fitts Law", "Movement time"),
            ("Fitts Law", "Movement time\ndepends on distance"),
            ("Fitts Law", "Movement time\ndepends on distance\nand target width"),
            ("Summary", "Review before the quiz"),
        ],
        page_numbers=True,
    )

    report, body = ingest_and_ask(lectures_dir, index_dir, "Fitts law movement time", top_k=20)

    assert (report.slides_read, report.duplicates_removed, report.passages) == (4, 2, 2)
    assert sorted(r["slide"] for r in body["retrieval"]) == [3, 4]
    assert "and target width" in body["retrieval"][0]["passage"]


def test_the_same_slide_in_two_lectures_is_kept_in_both(lectures_dir, index_dir):
    recap = ("Recap", "Fitts law predicts pointing time")
    make_lecture(lectures_dir / "Lecture 3 GOMS.pdf", [recap])
    make_lecture(lectures_dir / "Lecture 4 Vision.pdf", [recap])

    report, body = ingest_and_ask(lectures_dir, index_dir, "pointing time", top_k=20)

    assert report.duplicates_removed == 0
    assert {r["lecture"] for r in body["retrieval"]} == {"Lecture 3 GOMS", "Lecture 4 Vision"}


def test_consecutive_image_only_slides_are_not_duplicates(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 4 Vision.pdf",
        [("", ""), ("", ""), ("Colour perception", "Cones detect light")],
    )

    report, _ = ingest_and_ask(lectures_dir, index_dir, "cones", top_k=20)

    assert report.duplicates_removed == 0


def test_near_empty_slides_are_listed_but_still_indexed(lectures_dir, index_dir):
    title_only = ("Vision", "")
    image_only = ("", "")
    make_lecture(
        lectures_dir / "Lecture 4 Vision.pdf",
        [title_only, image_only] + SIX_SLIDES[:4],
        footer="Human Computer Interaction",  # on all 6 Slides, so it is a footer
        page_numbers=True,
    )

    report, _ = ingest_and_ask(lectures_dir, index_dir, "vision", top_k=20)

    assert report.near_empty == [("Lecture 4 Vision", 1), ("Lecture 4 Vision", 2)]
    assert report.passages == 6


def test_a_wrapped_word_repeated_in_the_slide_body_is_not_a_footer(lectures_dir, index_dir):
    # PDFs wrap "Supervised Learning" onto two lines, so "Learning" alone repeats a lot.
    wrapped = [(title, f"Supervised\nLearning\n{body}") for title, body in SIX_SLIDES]
    make_lecture(lectures_dir / "L1 Introduction to ML.pdf", wrapped)

    report, body = ingest_and_ask(lectures_dir, index_dir, "supervised learning", top_k=20)

    assert report.footers_removed == {}
    assert all("Learning" in r["passage"].splitlines() for r in body["retrieval"])


def test_bullet_only_lines_are_stripped_and_not_reported_as_footers(lectures_dir, index_dir):
    bulleted = [(title, f"•\n{body}") for title, body in SIX_SLIDES]
    make_lecture(lectures_dir / "Lecture 3 GOMS.pdf", bulleted)

    report, body = ingest_and_ask(lectures_dir, index_dir, "movement time", top_k=20)

    assert report.footers_removed == {}
    assert all("•" not in r["passage"].splitlines() for r in body["retrieval"])
