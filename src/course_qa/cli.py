"""Command line: `course-qa ingest` and `course-qa serve`.

Settings come from environment variables (see .env.example), overridable by flags.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from course_qa.config import RetrievalConfig


def _settings() -> dict[str, str]:
    load_dotenv()  # GROQ_API_KEY and COURSE_QA_* from .env, if present
    return {
        "lectures": os.environ.get("COURSE_QA_LECTURES_DIR", "data/raw"),
        "index": os.environ.get("COURSE_QA_INDEX_DIR", "data/index"),
        "config": os.environ.get("COURSE_QA_CONFIG", "eval/configs/baseline.yaml"),
        "llm_provider": os.environ.get("COURSE_QA_LLM_PROVIDER", "groq"),
        "answer_model": os.environ.get("COURSE_QA_ANSWER_MODEL", ""),
        "fallback_model": os.environ.get("COURSE_QA_FALLBACK_MODEL", ""),
        "reasoning_effort": os.environ.get("COURSE_QA_REASONING_EFFORT", ""),
        "ollama_url": os.environ.get("COURSE_QA_OLLAMA_URL", "http://localhost:11434"),
    }


def _answer_llm(s: dict[str, str]):
    """Groq's free tier by default; a local Ollama model when offline."""
    from course_qa.adapters import (
        DEFAULT_GROQ_FALLBACK_MODEL,
        DEFAULT_GROQ_MODEL,
        DEFAULT_OLLAMA_MODEL,
        DEFAULT_REASONING_EFFORT,
        GroqAnswerLLM,
        OllamaAnswerLLM,
    )

    if s["llm_provider"] == "ollama":
        return OllamaAnswerLLM(s["answer_model"] or DEFAULT_OLLAMA_MODEL, s["ollama_url"])
    if s["llm_provider"] == "groq":
        return GroqAnswerLLM(
            s["answer_model"] or DEFAULT_GROQ_MODEL,
            s["fallback_model"] or DEFAULT_GROQ_FALLBACK_MODEL,
            s["reasoning_effort"] or DEFAULT_REASONING_EFFORT,
        )
    raise SystemExit(f"COURSE_QA_LLM_PROVIDER must be 'groq' or 'ollama', not {s['llm_provider']!r}")


def create_service_app():
    """App factory for uvicorn: real models, settings from the environment."""
    from course_qa.adapters import SentenceTransformerEmbedder
    from course_qa.api import create_app

    s = _settings()
    config = RetrievalConfig.from_yaml(Path(s["config"]))
    return create_app(
        Path(s["index"]),
        config,
        SentenceTransformerEmbedder(config.embedding_model),
        _answer_llm(s),
        lectures_dir=Path(s["lectures"]),
    )


def main() -> None:
    s = _settings()
    parser = argparse.ArgumentParser(prog="course-qa")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Build the index from Lecture PDFs")
    ingest_p.add_argument("--lectures", default=s["lectures"])
    ingest_p.add_argument("--index", default=s["index"])
    ingest_p.add_argument("--config", default=s["config"])

    ladder_p = sub.add_parser("ladder", help="Score Retrieval Configurations on a split")
    ladder_p.add_argument("--eval-set", default="eval/sample_pairs.jsonl")
    ladder_p.add_argument("--configs", nargs="+", default=[s["config"]])
    ladder_p.add_argument("--lectures", default=s["lectures"])
    ladder_p.add_argument("--work-dir", default="data/ladder")
    ladder_p.add_argument("--split", choices=["dev", "test"], default="dev")
    ladder_p.add_argument("--unlock-test-split", action="store_true",
                          help="Only for the final reported run")
    ladder_p.add_argument("--answer", action="store_true",
                          help="Also answer every question with the LLM for Refusal metrics "
                               "(slower; subject to Groq free-tier rate limits)")
    ladder_p.add_argument("--out", default="results.md")

    plan_p = sub.add_parser("plan-drafts", help="Pick target Slides for Evaluation Set drafts")
    plan_p.add_argument("--index", default=s["index"])
    plan_p.add_argument("--count", type=int, default=200)
    plan_p.add_argument("--span-share", type=float, default=0.2)
    plan_p.add_argument("--seed", type=int, default=2026)
    plan_p.add_argument("--out", default="data/drafts/plan.jsonl",
                        help="Holds Slide text, so it stays in the git-ignored data folder")

    check_p = sub.add_parser("check-drafts", help="Flag drafts that copy Slide wording")
    check_p.add_argument("--drafts", default="eval/drafts.jsonl")
    check_p.add_argument("--index", default=s["index"])

    split_p = sub.add_parser("split", help="Make the fixed-seed Dev/Test Split from reviewed pairs")
    split_p.add_argument("--drafts", default="eval/drafts.jsonl")
    split_p.add_argument("--reviewed", default="eval/reviewed.jsonl")
    split_p.add_argument("--index", default=s["index"])
    split_p.add_argument("--seed", type=int, default=2026)
    split_p.add_argument("--out", default="eval/evaluation_set.jsonl")

    validate_p = sub.add_parser("validate", help="Check the whole Evaluation Set file")
    validate_p.add_argument("--eval-set", default="eval/evaluation_set.jsonl")
    validate_p.add_argument("--index", default=s["index"])

    serve_p = sub.add_parser("serve", help="Run the HTTP API")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    if args.command == "ingest":
        from course_qa.adapters import SentenceTransformerEmbedder
        from course_qa.ingest import ingest

        config = RetrievalConfig.from_yaml(Path(args.config))
        report = ingest(
            Path(args.lectures),
            Path(args.index),
            config,
            SentenceTransformerEmbedder(config.embedding_model),
        )
        print(f"Slides read:              {report.slides_read}")
        print(f"Duplicate Slides removed: {report.duplicates_removed}")
        print(f"Passages indexed:         {report.passages}")
        for lecture, footers in report.footers_removed.items():
            print(f"Footers removed from {lecture}: {', '.join(footers)}")
        print(f"Near-empty Slides:        {len(report.near_empty)}")
        for lecture, slide in report.near_empty:
            print(f"  {lecture} — Slide {slide}")
    elif args.command == "plan-drafts":
        import json
        from collections import Counter
        from dataclasses import asdict

        from course_qa.drafting import plan_drafts

        plan = plan_drafts(Path(args.index), args.count, args.span_share, args.seed)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(asdict(t), ensure_ascii=False) for t in plan) + "\n",
                       encoding="utf-8")
        print(f"{len(plan)} targets ({sum(t.kind == 'span' for t in plan)} span two Slides) -> {out}")
        for lecture, n in Counter(t.slides[0].lecture for t in plan).items():
            print(f"  {n:3}  {lecture}")
    elif args.command == "check-drafts":
        from course_qa.drafting import check_drafts

        checks = check_drafts(Path(args.drafts), Path(args.index))
        bad = [c for c in checks if c.copies_wording or c.unknown_gold_slides]
        for c in bad:
            reasons = []
            if c.copies_wording:
                reasons.append(f"copies {c.longest_shared_run} consecutive words from its Slide")
            if c.unknown_gold_slides:
                reasons.append(f"unknown Gold Slides {c.unknown_gold_slides}")
            print(f"{c.draft_id}: {'; '.join(reasons)}")
        print(f"{len(checks)} drafts checked, {len(bad)} flagged")
        raise SystemExit(1 if bad else 0)
    elif args.command == "split":
        from course_qa.evaluation_set import assign_splits
        from course_qa.review import ReviewSession

        review = ReviewSession(Path(args.drafts), Path(args.index), Path(args.reviewed))
        done, total = review.progress()
        kept = review.kept_pairs()
        if done < total:
            raise SystemExit(f"{total - done} drafts are still undecided; finish the review first.")
        pairs = assign_splits(kept, seed=args.seed)
        Path(args.out).write_text("\n".join(p.model_dump_json() for p in pairs) + "\n", encoding="utf-8")
        print(f"{sum(p.split == 'dev' for p in pairs)} dev / {sum(p.split == 'test' for p in pairs)} test "
              f"-> {args.out}")
    elif args.command == "validate":
        import json

        from course_qa.evaluation_set import validate_evaluation_set
        from course_qa.ingest import SLIDES_FILE

        slides = json.loads((Path(args.index) / SLIDES_FILE).read_text(encoding="utf-8"))
        problems = validate_evaluation_set(Path(args.eval_set), {(s["lecture"], s["slide"]) for s in slides})
        for p in problems:
            print(f"- {p}")
        print("Evaluation Set is valid." if not problems else f"{len(problems)} problems found.")
        raise SystemExit(1 if problems else 0)
    elif args.command == "ladder":
        from course_qa.adapters import SentenceTransformerEmbedder
        from course_qa.ladder import format_results, run_ladder

        embedders: dict[str, SentenceTransformerEmbedder] = {}
        rows = run_ladder(
            Path(args.eval_set),
            [RetrievalConfig.from_yaml(Path(c)) for c in args.configs],
            lectures_dir=Path(args.lectures),
            work_dir=Path(args.work_dir),
            embedder_for=lambda m: embedders.setdefault(m, SentenceTransformerEmbedder(m)),
            split=args.split,
            llm=_answer_llm(s) if args.answer else None,
            unlock_test_split=args.unlock_test_split,
        )
        table = format_results(rows)
        Path(args.out).write_text(table, encoding="utf-8")
        print(table)
    else:
        import uvicorn

        uvicorn.run(
            "course_qa.cli:create_service_app", factory=True, host=args.host, port=args.port
        )


if __name__ == "__main__":
    main()
