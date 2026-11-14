"""Retrieval: question in, ranked Passages out."""

from __future__ import annotations

import json
from pathlib import Path

import faiss
from pydantic import BaseModel

from course_qa.config import RetrievalConfig
from course_qa.ingest import DENSE_INDEX_FILE, PASSAGES_FILE
from course_qa.models import Embedder
from course_qa.passages import Passage


class RetrievedPassage(BaseModel):
    """A ranked Passage with the score each search method gave it."""

    passage: Passage
    scores: dict[str, float]


class Retriever:
    def __init__(self, index_dir: Path, config: RetrievalConfig, embedder: Embedder):
        index_dir = Path(index_dir)
        self._config = config
        self._embedder = embedder
        self._index = faiss.read_index(str(index_dir / DENSE_INDEX_FILE))
        self._passages = [
            Passage.model_validate(p)
            for p in json.loads((index_dir / PASSAGES_FILE).read_text(encoding="utf-8"))
        ]

    def retrieve(self, question: str) -> list[RetrievedPassage]:
        query = self._embedder.embed([question])
        k = min(self._config.top_k, len(self._passages))
        scores, ids = self._index.search(query, k)
        return [
            RetrievedPassage(passage=self._passages[i], scores={"dense": float(score)})
            for score, i in zip(scores[0], ids[0])
            if i >= 0
        ]
