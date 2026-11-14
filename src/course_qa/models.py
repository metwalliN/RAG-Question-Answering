"""Model boundaries: the only places the system touches embedding models and LLMs."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from pydantic import BaseModel


class GeneratedAnswer(BaseModel):
    """Structured LLM output. A Refusal is signalled only by ``refused``."""

    refused: bool
    answer: str


class MalformedLLMOutput(Exception):
    """The LLM's structured output could not be parsed."""


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return one L2-normalised float32 vector per text."""
        ...


class AnswerLLM(Protocol):
    def generate_answer(self, question: str, passages: list[str]) -> GeneratedAnswer:
        """Answer from the numbered Passages only (Passage 1 is ``passages[0]``)."""
        ...
