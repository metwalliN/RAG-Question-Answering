"""Retrieval Configurations: named, fixed settings that can be measured and compared."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class RetrievalConfig(BaseModel):
    name: str
    top_k: int = 5
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    @classmethod
    def from_yaml(cls, path: Path) -> "RetrievalConfig":
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
