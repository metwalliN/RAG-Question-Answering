"""Real implementations of the model boundaries in course_qa.models.

Imported only when the service or ingest runs for real; tests use fakes.
"""

from __future__ import annotations

import anthropic
import numpy as np
from pydantic import ValidationError

from course_qa.models import GeneratedAnswer, MalformedLLMOutput

ANSWER_SYSTEM_PROMPT = """\
You answer students' questions about a university course, using ONLY the numbered \
Passages from the course's lecture slides that you are given.

Rules:
- Write 2 to 6 sentences.
- After each claim, cite the Passage it came from with its number in square brackets, \
e.g. [2]. Cite only Passage numbers you were given.
- Use only what the Passages say. Do not add outside knowledge, even if you know it.
- If the Passages do not contain the answer, set "refused" to true and leave "answer" \
empty. Do not guess."""


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # heavy; optional extra

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.astype(np.float32)


class ClaudeAnswerLLM:
    def __init__(self, model: str = "claude-haiku-5-5", client: anthropic.Anthropic | None = None):
        self._model = model
        self._client = client or anthropic.Anthropic()

    def generate_answer(self, question: str, passages: list[str]) -> GeneratedAnswer:
        numbered = "\n\n".join(f"Passage [{i}]:\n{text}" for i, text in enumerate(passages, 1))
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=1024,
                system=ANSWER_SYSTEM_PROMPT,
                output_config={"effort": "low"},  # short, grounded answers; keeps latency down
                messages=[
                    {
                        "role": "user",
                        "content": f"{numbered}\n\nQuestion: {question}",
                    }
                ],
                output_format=GeneratedAnswer,
            )
        except ValidationError as exc:
            raise MalformedLLMOutput(str(exc)) from exc

        if response.stop_reason != "end_turn" or response.parsed_output is None:
            raise MalformedLLMOutput(f"no usable output (stop_reason={response.stop_reason})")
        return response.parsed_output
