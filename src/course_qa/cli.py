"""Command line: `course-qa ingest` and `course-qa serve`.

Settings come from environment variables (see .env.example), overridable by flags.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from course_qa.config import RetrievalConfig


def _settings() -> dict[str, str]:
    return {
        "lectures": os.environ.get("COURSE_QA_LECTURES_DIR", "data/raw"),
        "index": os.environ.get("COURSE_QA_INDEX_DIR", "data/index"),
        "config": os.environ.get("COURSE_QA_CONFIG", "eval/configs/baseline.yaml"),
        "answer_model": os.environ.get("COURSE_QA_ANSWER_MODEL", "claude-haiku-5-5"),
    }


def create_service_app():
    """App factory for uvicorn: real models, settings from the environment."""
    from course_qa.adapters import ClaudeAnswerLLM, SentenceTransformerEmbedder
    from course_qa.api import create_app

    s = _settings()
    config = RetrievalConfig.from_yaml(Path(s["config"]))
    return create_app(
        Path(s["index"]),
        config,
        SentenceTransformerEmbedder(config.embedding_model),
        ClaudeAnswerLLM(s["answer_model"]),
    )


def main() -> None:
    s = _settings()
    parser = argparse.ArgumentParser(prog="course-qa")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Build the index from Lecture PDFs")
    ingest_p.add_argument("--lectures", default=s["lectures"])
    ingest_p.add_argument("--index", default=s["index"])
    ingest_p.add_argument("--config", default=s["config"])

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
    else:
        import uvicorn

        uvicorn.run(
            "course_qa.cli:create_service_app", factory=True, host=args.host, port=args.port
        )


if __name__ == "__main__":
    main()
