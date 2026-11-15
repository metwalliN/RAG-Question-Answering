"""Answering: retrieved Passages plus the LLM's structured output become a cited answer."""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel

from course_qa.models import AnswerLLM
from course_qa.passages import Passage

log = logging.getLogger(__name__)

_MARKER = re.compile(r"\s*\[(\d+)\]")  # with its leading space, for removal
_BARE_MARKER = re.compile(r"\[(\d+)\]")

_SENTENCE_ENDS = (".", ":", ";", "?", "!")
_STARTS_ITEM = re.compile(r"^([•·▪◦❖►➢✓–—*-]|\d+[.)]\s)")

REFUSAL_TEXT = "The Course Material doesn't answer this question."


class Citation(BaseModel):
    marker: int
    lecture: str
    slide: int
    passage: str


class Answer(BaseModel):
    answer: str
    refused: bool
    citations: list[Citation]


def answer_question(question: str, passages: list[Passage], llm: AnswerLLM) -> Answer:
    generated = llm.generate_answer(question, [p.text for p in passages])
    if generated.refused:
        return refusal()
    text = _remove_dangling_markers(generated.answer, len(passages))
    # Renumber markers 1, 2, ... in order of first appearance, not by retrieval rank.
    order = list(dict.fromkeys(int(m) for m in _BARE_MARKER.findall(text)))
    renumbered = {old: new for new, old in enumerate(order, start=1)}
    text = _BARE_MARKER.sub(lambda m: f"[{renumbered[int(m.group(1))]}]", text)
    citations = [
        Citation(
            marker=renumbered[old],
            lecture=passages[old - 1].lecture,
            slide=passages[old - 1].slide,
            passage=reflow(passages[old - 1].text),
        )
        for old in order
    ]
    return Answer(answer=text, refused=False, citations=citations)


def reflow(text: str) -> str:
    """Join lines the PDF layout wrapped mid-sentence, for display in a Citation.

    A line continues the previous one when that line doesn't end a sentence and this one
    starts in lowercase, or when the previous line ends in a hyphen. Bullets always start
    a new line.
    """
    out: list[str] = []
    for line in text.splitlines():
        if out and not _STARTS_ITEM.match(line):
            prev = out[-1]
            if prev.endswith("-") and line[:1].isalpha():
                out[-1] = prev + line
                continue
            if not prev.endswith(_SENTENCE_ENDS) and line[:1].islower():
                out[-1] = f"{prev} {line}"
                continue
        out.append(line)
    return "\n".join(out)


def refusal() -> Answer:
    return Answer(answer=REFUSAL_TEXT, refused=True, citations=[])


def _remove_dangling_markers(text: str, passage_count: int) -> str:
    """Drop ``[n]`` markers that point at no supplied Passage."""

    def keep_or_drop(match: re.Match) -> str:
        if 1 <= int(match.group(1)) <= passage_count:
            return match.group(0)
        log.warning("Removed Citation marker [%s] pointing at no Passage", match.group(1))
        return ""

    return _MARKER.sub(keep_or_drop, text)
