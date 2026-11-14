"""Retrieval Configurations: named, fixed settings that can be measured and compared."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class CleaningSettings(BaseModel):
    """How ingest cleans Slide text before building Passages."""

    # A deck footer (or header) is a line in the page margin, repeated across a Lecture:
    footer_margin: float = 0.08  # within this share of the page height from top or bottom,
    footer_min_share: float = 0.10  # on at least this share of the Lecture's Slides,
    footer_min_count: int = 5  # and on at least this many Slides.
    near_empty_chars: int = 20  # Slides with less text than this beyond the title


class RetrievalConfig(BaseModel):
    name: str
    top_k: int = 5
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    cleaning: CleaningSettings = CleaningSettings()

    @classmethod
    def from_yaml(cls, path: Path) -> "RetrievalConfig":
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
