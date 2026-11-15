"""Seam 1: ingest Course Material, then ask through the HTTP API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from course_qa.answering import REFUSAL_TEXT
from course_qa.api import create_app
from course_qa.config import RetrievalConfig
from course_qa.ingest import ingest
from conftest import make_lecture
from fakes import FakeEmbedder, ScriptedLLM

BASELINE = RetrievalConfig(name="baseline", top_k=5)


def build_client(lectures_dir, index_dir, llm, config=BASELINE):
    embedder = FakeEmbedder()
    ingest(lectures_dir, index_dir, config, embedder)
    return TestClient(create_app(index_dir, config, embedder, llm, lectures_dir=lectures_dir))


def test_answer_cites_the_lecture_and_slide_it_came_from(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "Lecture 1 Intro.pdf",
        [
            ("Welcome", "Course overview and grading policy"),
            ("Fitts Law", "Movement time depends on distance and target width"),
        ],
    )
    make_lecture(
        lectures_dir / "Lecture 2 Vision.pdf",
        [("Colour perception", "Cones detect red green and blue light")],
    )
    llm = ScriptedLLM(answer="Movement time grows with distance to the target [1].")
    client = build_client(lectures_dir, index_dir, llm)

    body = client.post("/ask", json={"question": "What does movement time depend on?"}).json()

    assert body["refused"] is False
    assert body["answer"] == "Movement time grows with distance to the target [1]."
    assert [(c["marker"], c["lecture"], c["slide"]) for c in body["citations"]] == [
        (1, "Lecture 1 Intro", 2)
    ]
    assert "Movement time depends on distance" in body["citations"][0]["passage"]


def two_lecture_course(lectures_dir):
    make_lecture(
        lectures_dir / "Lecture 1 Intro.pdf",
        [
            ("Welcome", "Course overview and grading policy"),
            ("Fitts Law", "Movement time depends on distance and target width"),
        ],
    )
    make_lecture(
        lectures_dir / "Lecture 2 Vision.pdf",
        [("Colour perception", "Cones detect red green and blue light")],
    )


def test_markers_pointing_at_no_passage_are_removed(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    llm = ScriptedLLM(answer="Movement time grows with distance [1] and with luck [9].")
    client = build_client(lectures_dir, index_dir, llm)

    body = client.post("/ask", json={"question": "What does movement time depend on?"}).json()

    assert body["answer"] == "Movement time grows with distance [1] and with luck."
    assert [c["marker"] for c in body["citations"]] == [1]


def test_llm_signalled_refusal_has_standard_text_and_no_citations(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    llm = ScriptedLLM(refused=True, answer="The slides only mention grading [1].")
    client = build_client(lectures_dir, index_dir, llm)

    body = client.post("/ask", json={"question": "When is the final exam?"}).json()

    assert body["refused"] is True
    assert body["answer"] == REFUSAL_TEXT
    assert body["citations"] == []


def test_refusal_sounding_text_is_not_a_refusal_unless_flagged(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    llm = ScriptedLLM(answer="This is not in the Passages, but cones detect colour [1].")
    client = build_client(lectures_dir, index_dir, llm)

    body = client.post("/ask", json={"question": "What do cones detect?"}).json()

    assert body["refused"] is False
    assert body["answer"] == "This is not in the Passages, but cones detect colour [1]."


def test_malformed_llm_output_is_an_error_not_a_guess(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    client = build_client(lectures_dir, index_dir, ScriptedLLM(malformed=True))

    response = client.post("/ask", json={"question": "What do cones detect?"})

    assert response.status_code == 502
    assert "malformed" in response.json()["detail"].lower()


def test_response_lists_retrieved_passages_with_scores_and_timings(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    client = build_client(lectures_dir, index_dir, ScriptedLLM(answer="Cones [1]."))

    body = client.post("/ask", json={"question": "What do cones detect?"}).json()

    top = body["retrieval"][0]
    assert (top["lecture"], top["slide"]) == ("Lecture 2 Vision", 1)
    assert "Cones detect red green and blue light" in top["passage"]
    assert set(top["scores"]) == {"dense"}
    assert len(body["retrieval"]) == 3  # every Slide in this tiny course, ranked
    assert set(body["timings_ms"]) == {"retrieve", "rerank", "generate", "total"}
    assert body["timings_ms"]["rerank"] == 0  # the Baseline has no reranker
    assert body["timings_ms"]["total"] >= body["timings_ms"]["generate"]


def test_health_reports_ok_once_the_index_is_loaded(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    client = build_client(lectures_dir, index_dir, ScriptedLLM())

    assert client.get("/health").json() == {"status": "ok"}



def test_lectures_in_course_subfolders_are_ingested(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "hci" / "Lecture 4 Vision.pdf",
        [("Colour perception", "Cones detect red green and blue light")],
    )
    make_lecture(
        lectures_dir / "ml" / "L1 Introduction.pdf",
        [("Supervised learning", "Learning a mapping from labelled examples")],
    )
    client = build_client(lectures_dir, index_dir, ScriptedLLM(answer="See [1]."))

    body = client.post("/ask", json={"question": "What is supervised learning?"}).json()

    assert {(r["lecture"], r["slide"]) for r in body["retrieval"]} == {
        ("Lecture 4 Vision", 1),
        ("L1 Introduction", 1),
    }


def test_citation_markers_are_renumbered_in_order_of_first_appearance(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    llm = ScriptedLLM(answer="Cones see colour [3]. Rods differ [1]. Cones again [3].")
    client = build_client(lectures_dir, index_dir, llm)

    body = client.post("/ask", json={"question": "What do cones detect?"}).json()

    assert body["answer"] == "Cones see colour [1]. Rods differ [2]. Cones again [1]."
    ranked = [(r["lecture"], r["slide"]) for r in body["retrieval"]]
    assert [(c["marker"], c["lecture"], c["slide"]) for c in body["citations"]] == [
        (1, *ranked[2]),  # the answer's first marker was retrieval rank 3
        (2, *ranked[0]),
    ]


def test_citation_passages_join_lines_wrapped_only_by_the_pdf_layout(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "L01 Introduction to ML.pdf",
        [(
            "Soft Computing",
            "Hard computing is like solving a mathematical\n"
            "equation with a definite solution.\n"
            "• Or like writing conditional\n"
            "statements for every case\n"
            "• Left-\n"
            "Power is averaged per band",
        )],
    )
    client = build_client(lectures_dir, index_dir, ScriptedLLM(answer="Hard computing [1]."))

    body = client.post("/ask", json={"question": "What is hard computing?"}).json()

    lines = body["citations"][0]["passage"].splitlines()
    assert "Hard computing is like solving a mathematical equation with a definite solution." in lines
    # (the fixture font draws "•" as "·"; either way each bullet keeps its own line)
    assert any(line.endswith(" Or like writing conditional statements for every case") for line in lines)
    assert any(line.endswith(" Left-Power is averaged per band") for line in lines)
    assert "statements for every case" in body["retrieval"][0]["passage"].splitlines()  # raw kept


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_a_cited_slide_can_be_fetched_as_a_rendered_image(lectures_dir, index_dir):
    two_lecture_course(lectures_dir)
    client = build_client(lectures_dir, index_dir, ScriptedLLM(answer="Cones [1]."))
    cited = client.post("/ask", json={"question": "What do cones detect?"}).json()["citations"][0]

    image = client.get("/slides/image", params={"lecture": cited["lecture"], "slide": cited["slide"]})

    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(PNG_SIGNATURE)


def test_only_indexed_slides_can_be_fetched_as_images(lectures_dir, index_dir):
    make_lecture(
        lectures_dir / "L03 GOMS.pdf",
        [("Fitts Law", "Movement time"), ("Fitts Law", "Movement time\ndepends on distance")],
    )
    client = build_client(lectures_dir, index_dir, ScriptedLLM())

    removed_build_step = client.get("/slides/image", params={"lecture": "L03 GOMS", "slide": 1})
    unknown_lecture = client.get("/slides/image", params={"lecture": "L99 Nothing", "slide": 1})

    assert (removed_build_step.status_code, unknown_lecture.status_code) == (404, 404)
