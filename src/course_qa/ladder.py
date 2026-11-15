"""The ladder runner: score each Retrieval Configuration on one split of the Evaluation Set."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from course_qa.answering import answer_question
from course_qa.config import RetrievalConfig
from course_qa.evaluation_set import Split, load_evaluation_set
from course_qa.ingest import ingest
from course_qa.models import AnswerLLM, Embedder
from course_qa.retrieval import Retriever
from course_qa.scoring import PairOutcome, Scores, score


class TestSplitLocked(Exception):
    """The Test Split is only scored for reported results, and only on explicit request."""

    __test__ = False  # not a pytest test class, despite the name


@dataclass(frozen=True)
class LadderRow:
    config: str
    split: Split
    pairs: int
    scores: Scores


def run_ladder(
    eval_set: Path,
    configs: list[RetrievalConfig],
    *,
    lectures_dir: Path,
    work_dir: Path,
    embedder_for: Callable[[str], Embedder],
    split: Split = "dev",
    llm: AnswerLLM | None = None,
    unlock_test_split: bool = False,
) -> list[LadderRow]:
    """Score each configuration. Without ``llm``, only retrieval is measured (no LLM calls)."""
    if split == "test" and not unlock_test_split:
        raise TestSplitLocked(
            "The Test Split is held out for reported results. "
            "Tune on the Dev Split; unlock the Test Split only for the final run."
        )
    pairs = [p for p in load_evaluation_set(eval_set) if p.split == split]
    rows = []
    for config in configs:
        embedder = embedder_for(config.embedding_model)
        index_dir = Path(work_dir) / config.name
        ingest(lectures_dir, index_dir, config, embedder)
        retriever = Retriever(index_dir, config, embedder)
        outcomes = []
        for p in pairs:
            retrieved = retriever.retrieve(p.question)
            refused = None
            if llm is not None:
                refused = answer_question(p.question, [r.passage for r in retrieved], llm).refused
            outcomes.append(
                PairOutcome(
                    ranked_slides=[(r.passage.lecture, r.passage.slide) for r in retrieved],
                    gold_slides={(g.lecture, g.slide) for g in p.gold_slides},
                    unanswerable=p.unanswerable,
                    refused=refused,
                )
            )
        rows.append(LadderRow(config.name, split, len(pairs), score(outcomes)))
    return rows


def format_results(rows: list[LadderRow]) -> str:
    """A Markdown results table; "—" marks a metric the run didn't measure."""
    lines = [
        "| Retrieval Configuration | Split | Pairs | Recall@5 | MRR | Refusal accuracy | False Refusal rate |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r.scores
        cells = [
            r.config,
            r.split,
            str(r.pairs),
            _percent(s.recall_at_5),
            "—" if s.mrr is None else f"{s.mrr:.3f}",
            _percent(s.refusal_accuracy),
            _percent(s.false_refusal_rate),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"
