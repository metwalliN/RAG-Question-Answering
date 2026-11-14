"""Opt-in: the real bge-small embedder over fixture Lectures (`pytest -m slow`)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import make_lecture
from course_qa.api import create_app
from course_qa.config import RetrievalConfig
from course_qa.ingest import ingest
from fakes import ScriptedLLM

pytestmark = pytest.mark.slow


def test_real_embedder_retrieves_the_paraphrased_slide(lectures_dir, index_dir):
    from course_qa.adapters import SentenceTransformerEmbedder

    make_lecture(
        lectures_dir / "Lecture 1 Intro.pdf",
        [
            ("Fitts Law", "Movement time depends on distance and target width"),
            ("Colour perception", "Cones detect red green and blue light"),
        ],
    )
    config = RetrievalConfig.from_yaml("eval/configs/baseline.yaml")
    embedder = SentenceTransformerEmbedder(config.embedding_model)
    ingest(lectures_dir, index_dir, config, embedder)
    client = TestClient(create_app(index_dir, config, embedder, ScriptedLLM(answer="[1]")))

    body = client.post("/ask", json={"question": "How long does it take to point at a button?"}).json()

    assert (body["retrieval"][0]["lecture"], body["retrieval"][0]["slide"]) == ("Lecture 1 Intro", 1)
