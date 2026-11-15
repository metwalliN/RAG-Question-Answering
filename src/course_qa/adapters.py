"""Real implementations of the model boundaries in course_qa.models.

Imported only when the service or ingest runs for real; tests use fakes.
Answering runs on free infrastructure: Groq's free tier (gpt-oss) by default,
or a local Ollama model as an offline fallback.
"""

from __future__ import annotations

import logging

import numpy as np
import requests
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
empty. Do not guess.

Reply with a JSON object and nothing else: {"refused": true or false, "answer": "..."}"""

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"
DEFAULT_REASONING_EFFORT = "low"  # short, grounded answers; keeps latency down
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"

log = logging.getLogger(__name__)


def _answer_messages(question: str, passages: list[str]) -> list[dict[str, str]]:
    numbered = "\n\n".join(f"Passage [{i}]:\n{text}" for i, text in enumerate(passages, 1))
    return [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": f"{numbered}\n\nQuestion: {question}"},
    ]


def _parse_answer(raw: str | None) -> GeneratedAnswer:
    """Strictly parse the model's JSON. Anything else is malformed, never guessed at."""
    if not raw:
        raise MalformedLLMOutput("empty response")
    try:
        return GeneratedAnswer.model_validate_json(raw)
    except ValidationError as exc:
        raise MalformedLLMOutput(str(exc)) from exc


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # heavy; optional extra

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.astype(np.float32)


class GroqAnswerLLM:
    """Groq's free tier. Reads GROQ_API_KEY from the environment.

    If the primary model fails (an API error, a rate limit, or malformed output), the same
    request is retried once on the fallback model.
    """

    def __init__(
        self,
        model: str = DEFAULT_GROQ_MODEL,
        fallback_model: str | None = DEFAULT_GROQ_FALLBACK_MODEL,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    ):
        from groq import Groq

        self._models = [model] + ([fallback_model] if fallback_model and fallback_model != model else [])
        self._reasoning_effort = reasoning_effort
        self._client = Groq(max_retries=1)  # fail over to the fallback model quickly

    def generate_answer(self, question: str, passages: list[str]) -> GeneratedAnswer:
        import groq

        messages = _answer_messages(question, passages)
        for attempt, model in enumerate(self._models):
            try:
                return self._ask(model, messages)
            except (groq.APIStatusError, groq.APIConnectionError, MalformedLLMOutput) as exc:
                if attempt == len(self._models) - 1:
                    raise MalformedLLMOutput(f"{model} failed: {type(exc).__name__}") from exc
                log.warning("%s failed (%s); falling back to %s",
                            model, type(exc).__name__, self._models[attempt + 1])
        raise AssertionError("unreachable")

    def _ask(self, model: str, messages: list[dict[str, str]]) -> GeneratedAnswer:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort=self._reasoning_effort,
            include_reasoning=False,
            temperature=0,
            max_completion_tokens=2048,
        )
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise MalformedLLMOutput(f"no usable output (finish_reason={choice.finish_reason})")
        log.info("answered by %s", model)
        return _parse_answer(choice.message.content)


class OllamaAnswerLLM:
    """A local model served by Ollama; works offline once the model is pulled."""

    def __init__(self, model: str = DEFAULT_OLLAMA_MODEL, url: str = "http://localhost:11434"):
        self._model = model
        self._url = url.rstrip("/")

    def generate_answer(self, question: str, passages: list[str]) -> GeneratedAnswer:
        response = requests.post(
            f"{self._url}/api/chat",
            json={
                "model": self._model,
                "messages": _answer_messages(question, passages),
                "format": GeneratedAnswer.model_json_schema(),
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        response.raise_for_status()
        return _parse_answer(response.json().get("message", {}).get("content"))
