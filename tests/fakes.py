"""Deterministic stand-ins for the model boundaries (embedder, LLM).

Tests never download models or call an LLM service.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import numpy as np

from course_qa.models import GeneratedAnswer, MalformedLLMOutput

_DIM = 256


class FakeEmbedder:
    """Bag-of-words hashing embedder: texts sharing words get similar vectors."""

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), _DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % _DIM
                vectors[row, bucket] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


@dataclass
class ScriptedLLM:
    """Returns a fixed structured output and records every call."""

    answer: str = ""
    refused: bool = False
    malformed: bool = False
    calls: list[dict] = field(default_factory=list)

    def generate_answer(self, question: str, passages: list[str]) -> GeneratedAnswer:
        self.calls.append({"question": question, "passages": passages})
        if self.malformed:
            raise MalformedLLMOutput("scripted malformed output")
        return GeneratedAnswer(refused=self.refused, answer=self.answer)
