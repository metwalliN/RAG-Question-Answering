"""Seam 3: the ladder runner, from an Evaluation Set file to a results table."""

from __future__ import annotations

import json

import pytest

from conftest import make_lecture
from course_qa.config import RetrievalConfig
from course_qa.evaluation_set import InvalidEvaluationSet
from course_qa.ladder import TestSplitLocked, format_results, run_ladder
from fakes import FakeEmbedder, ScriptedLLM

BASELINE = RetrievalConfig(name="baseline", top_k=5)


def pair(pid, question, gold=(), split="dev", unanswerable=False):
    return {
        "id": pid,
        "question": question,
        "reference_answer": "…",
        "gold_slides": [{"lecture": lecture, "slide": slide} for lecture, slide in gold],
        "unanswerable": unanswerable,
        "origin": "hand-written",
        "split": split,
    }


@pytest.fixture
def course(lectures_dir):
    make_lecture(
        lectures_dir / "Lecture 3 GOMS.pdf",
        [
            ("Fitts Law", "Movement time depends on distance and target width"),
            ("Hick Law", "Decision time grows with the number of choices"),
        ],
    )
    make_lecture(
        lectures_dir / "Lecture 4 Vision.pdf",
        [("Colour perception", "Cones detect red green and blue light")],
    )
    return lectures_dir


def write_eval_set(path, pairs):
    path.write_text("\n".join(json.dumps(p) for p in pairs), encoding="utf-8")
    return path


def run(course, tmp_path, pairs, **kwargs):
    eval_set = write_eval_set(tmp_path / "eval.jsonl", pairs)
    return run_ladder(
        eval_set,
        kwargs.pop("configs", [BASELINE]),
        lectures_dir=course,
        work_dir=tmp_path / "work",
        embedder_for=lambda model_name: FakeEmbedder(),
        **kwargs,
    )


SAMPLE = [
    pair("d1", "What does movement time depend on?", gold=[("Lecture 3 GOMS", 1)]),
    pair("d2", "What do cones detect?", gold=[("Lecture 4 Vision", 1)]),
    pair("d3", "When is the final exam?", unanswerable=True),
    pair("t1", "How does decision time grow?", gold=[("Lecture 3 GOMS", 2)], split="test"),
]


def test_the_baseline_row_scores_only_the_dev_split(course, tmp_path):
    rows = run(course, tmp_path, SAMPLE)

    [row] = rows
    assert (row.config, row.split, row.pairs) == ("baseline", "dev", 3)
    assert (row.scores.recall_at_5, row.scores.mrr) == (1.0, 1.0)


def test_without_answering_refusal_metrics_are_not_measured(course, tmp_path):
    [row] = run(course, tmp_path, SAMPLE)

    assert (row.scores.refusal_accuracy, row.scores.false_refusal_rate) == (None, None)


def test_answer_mode_measures_refusals_from_the_assistants_answers(course, tmp_path):
    always_refuses = ScriptedLLM(refused=True)

    [row] = run(course, tmp_path, SAMPLE, llm=always_refuses)

    assert (row.scores.refusal_accuracy, row.scores.false_refusal_rate) == (1.0, 1.0)
    assert len(always_refuses.calls) == 3  # every Dev Split pair, nothing from the Test Split


def test_the_test_split_is_locked_unless_explicitly_unlocked(course, tmp_path):
    with pytest.raises(TestSplitLocked):
        run(course, tmp_path, SAMPLE, split="test")

    [row] = run(course, tmp_path, SAMPLE, split="test", unlock_test_split=True)
    assert (row.split, row.pairs) == ("test", 1)


@pytest.mark.parametrize(
    "bad_pair",
    [
        pair("d9", "When is the exam?", gold=[("Lecture 3 GOMS", 1)], unanswerable=True),
        pair("d9", "What is Fitts law?", gold=[]),  # answerable, but no Gold Slide
    ],
)
def test_an_inconsistent_evaluation_pair_is_rejected_by_id(course, tmp_path, bad_pair):
    with pytest.raises(InvalidEvaluationSet, match="d9"):
        run(course, tmp_path, SAMPLE + [bad_pair])


def test_the_results_table_has_one_row_per_configuration(course, tmp_path):
    configs = [BASELINE, RetrievalConfig(name="top-1", top_k=1)]

    rows = run(course, tmp_path, SAMPLE, configs=configs)

    assert format_results(rows) == (
        "| Retrieval Configuration | Split | Pairs | Recall@5 | MRR | Refusal accuracy | False Refusal rate |\n"
        "|---|---|---|---|---|---|---|\n"
        "| baseline | dev | 3 | 100.0% | 1.000 | — | — |\n"
        "| top-1 | dev | 3 | 100.0% | 1.000 | — | — |\n"
    )
