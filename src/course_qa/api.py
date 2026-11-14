"""HTTP API: POST /ask and GET /health."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from course_qa.answering import Citation, answer_question
from course_qa.config import RetrievalConfig
from course_qa.models import AnswerLLM, Embedder, MalformedLLMOutput
from course_qa.retrieval import Retriever


class AskRequest(BaseModel):
    question: str


class RetrievalEntry(BaseModel):
    lecture: str
    slide: int
    passage: str
    scores: dict[str, float]


class Timings(BaseModel):
    retrieve: float
    rerank: float
    generate: float
    total: float


class AskResponse(BaseModel):
    answer: str
    refused: bool
    citations: list[Citation]
    retrieval: list[RetrievalEntry]
    timings_ms: Timings


def _ms_since(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def create_app(
    index_dir: Path, config: RetrievalConfig, embedder: Embedder, llm: AnswerLLM
) -> FastAPI:
    retriever = Retriever(index_dir, config, embedder)
    app = FastAPI(title="Course Q&A Assistant")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(request: AskRequest) -> AskResponse:
        started = time.perf_counter()
        retrieved = retriever.retrieve(request.question)
        retrieve_ms = _ms_since(started)

        generate_started = time.perf_counter()
        try:
            answer = answer_question(request.question, [r.passage for r in retrieved], llm)
        except MalformedLLMOutput as exc:
            raise HTTPException(status_code=502, detail=f"LLM returned malformed output: {exc}")
        generate_ms = _ms_since(generate_started)

        return AskResponse(
            **answer.model_dump(),
            retrieval=[
                RetrievalEntry(
                    lecture=r.passage.lecture,
                    slide=r.passage.slide,
                    passage=r.passage.text,
                    scores=r.scores,
                )
                for r in retrieved
            ],
            timings_ms=Timings(
                retrieve=retrieve_ms, rerank=0, generate=generate_ms, total=_ms_since(started)
            ),
        )

    return app
