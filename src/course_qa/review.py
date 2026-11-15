"""The review session: the developer's accept / edit / reject decisions on drafts.

Every decision is appended to the reviewed file at once, so a review can stop at any
point and resume at the first undecided draft. A later decision on the same draft
overrides an earlier one. The Streamlit review page is a thin view over this class.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from course_qa.drafting import Draft, load_drafts
from course_qa.evaluation_set import GoldSlide, ReviewedPair
from course_qa.ingest import SLIDES_FILE
from course_qa.slide_images import UnknownSlide


class Decision(BaseModel):
    draft_id: str  # the draft's id, or a hand-written pair's own id
    decision: str  # "accepted", "edited", "rejected" or "hand-written"
    pair: ReviewedPair | None = None  # None for a rejected draft
    reason: str = ""


class ReviewSession:
    def __init__(self, drafts: Path, index_dir: Path, reviewed: Path):
        self._drafts = load_drafts(drafts)
        self._by_id = {d.id: d for d in self._drafts}
        slides = json.loads((Path(index_dir) / SLIDES_FILE).read_text(encoding="utf-8"))
        self._slides = {(s["lecture"], s["slide"]) for s in slides}
        self._reviewed = Path(reviewed)
        self._decisions: dict[str, Decision] = {}
        if self._reviewed.exists():
            for line in self._reviewed.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    d = Decision.model_validate_json(line)
                    self._decisions[d.draft_id] = d

    def next_draft(self) -> Draft | None:
        """The first draft without a decision, or None when the review is done."""
        return next((d for d in self._drafts if d.id not in self._decisions), None)

    def accept(self, draft_id: str, note: str = "") -> None:
        """``note`` records context, e.g. that the decision came from Claude Code's second pass."""
        draft = self._by_id[draft_id]
        self._record(
            Decision(draft_id=draft_id, decision="accepted", pair=self._pair(draft), reason=note)
        )

    def reject(self, draft_id: str, reason: str = "") -> None:
        self._by_id[draft_id]  # an unknown id is an error, not a silent no-op
        self._record(Decision(draft_id=draft_id, decision="rejected", reason=reason))

    def add_hand_written(
        self,
        question: str,
        reference_answer: str,
        gold_slides: list[tuple[str, int]],
        unanswerable: bool = False,
    ) -> ReviewedPair:
        """Add the developer's own pair; an Unanswerable Question has no Gold Slides."""
        count = sum(d.decision == "hand-written" for d in self._decisions.values())
        pair = ReviewedPair(
            id=f"h{count + 1:03d}",
            question=question,
            reference_answer=reference_answer,
            gold_slides=self._checked(gold_slides),
            unanswerable=unanswerable,
            origin="hand-written",
        )
        self._record(Decision(draft_id=pair.id, decision="hand-written", pair=pair))
        return pair

    def kept_pairs(self) -> list[ReviewedPair]:
        """Every accepted, edited or hand-written pair, by its latest decision."""
        return [d.pair for d in self._decisions.values() if d.pair is not None]

    def progress(self) -> tuple[int, int]:
        """(drafts decided, drafts in total)."""
        return sum(d.id in self._decisions for d in self._drafts), len(self._drafts)

    def edit(
        self,
        draft_id: str,
        *,
        question: str | None = None,
        reference_answer: str | None = None,
        gold_slides: list[tuple[str, int]] | None = None,
        note: str = "",
    ) -> None:
        """Accept a draft with changes; fields left as None keep the draft's value."""
        draft = self._by_id[draft_id]
        pair = self._pair(draft)
        if question is not None:
            pair.question = question
        if reference_answer is not None:
            pair.reference_answer = reference_answer
        if gold_slides is not None:
            pair.gold_slides = self._checked(gold_slides)
            # A Gold Slide on a drafted Unanswerable Question means the course does answer it.
            pair.unanswerable = not pair.gold_slides
        self._record(Decision(draft_id=draft_id, decision="edited", pair=pair, reason=note))

    def _checked(self, gold_slides: list[tuple[str, int]]) -> list[GoldSlide]:
        unknown = [g for g in gold_slides if tuple(g) not in self._slides]
        if unknown:
            raise UnknownSlide(f"not in the current ingest: {unknown}")
        return [GoldSlide(lecture=lecture, slide=slide) for lecture, slide in gold_slides]

    def _pair(self, draft: Draft) -> ReviewedPair:
        return ReviewedPair(
            id=draft.id,
            question=draft.question,
            reference_answer=draft.reference_answer,
            gold_slides=draft.gold_slides,
            unanswerable=draft.unanswerable,
            origin="drafted-and-reviewed",
        )

    def _record(self, decision: Decision) -> None:
        self._decisions[decision.draft_id] = decision
        self._reviewed.parent.mkdir(parents=True, exist_ok=True)
        with self._reviewed.open("a", encoding="utf-8") as f:
            f.write(decision.model_dump_json() + "\n")
