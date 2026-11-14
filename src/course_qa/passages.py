from __future__ import annotations

from pydantic import BaseModel


class Passage(BaseModel):
    """A span of Lecture text, belonging to exactly one Anchor Slide."""

    lecture: str
    slide: int  # the Anchor Slide's number
    text: str
