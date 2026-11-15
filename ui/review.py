"""Evaluation Set review page: one draft at a time, Accept / Edit / Reject.

Run with:  python -m uv run streamlit run ui/review.py
Every decision is saved immediately to the reviewed file, so you can stop and resume.
This page reads your local files directly (no API server needed).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from course_qa.ingest import SLIDES_FILE
from course_qa.review import ReviewSession
from course_qa.slide_images import SlideImages

DRAFTS = Path(os.environ.get("COURSE_QA_DRAFTS", "eval/drafts.jsonl"))
REVIEWED = Path(os.environ.get("COURSE_QA_REVIEWED", "eval/reviewed.jsonl"))
INDEX = Path(os.environ.get("COURSE_QA_INDEX_DIR", "data/index"))
LECTURES = Path(os.environ.get("COURSE_QA_LECTURES_DIR", "data/raw"))

st.set_page_config(page_title="Evaluation Set Review", page_icon="📝", layout="wide")


@st.cache_resource
def slide_data() -> tuple[dict[tuple[str, int], dict], SlideImages]:
    slides = json.loads((INDEX / SLIDES_FILE).read_text(encoding="utf-8"))
    return {(s["lecture"], s["slide"]): s for s in slides}, SlideImages(INDEX, LECTURES)


@st.cache_data(show_spinner=False)
def slide_png(lecture: str, slide: int) -> bytes:
    return slide_data()[1].render_png(lecture, slide, width=720)


def label(key: tuple[str, int]) -> str:
    return f"{key[0]} — Slide {key[1]}"


slides, _ = slide_data()
review = ReviewSession(DRAFTS, INDEX, REVIEWED)
done, total = review.progress()
kept = review.kept_pairs()

st.sidebar.title("Review progress")
st.sidebar.progress(done / total if total else 1.0, text=f"{done} of {total} drafts decided")
st.sidebar.metric("Pairs kept so far", len(kept))
st.sidebar.caption(
    f"{sum(p.origin == 'hand-written' for p in kept)} hand-written, "
    f"{sum(p.unanswerable for p in kept)} Unanswerable. Target: 150 pairs in total."
)

draft = review.next_draft()
if draft is None:
    st.title("All drafts reviewed")
    st.success(f"{len(kept)} pairs kept. Add hand-written pairs below, then run "
               "`python -m uv run course-qa split` to make the Dev and Test Splits.")
else:
    kinds = {"span": "two Slides", "single": "one Slide", "unanswerable": "Unanswerable Question"}
    st.title(f"Draft {draft.id}  ·  {kinds.get(draft.kind, draft.kind)}")

    gold_key = f"gold-{draft.id}"
    if gold_key not in st.session_state:
        st.session_state[gold_key] = [(g.lecture, g.slide) for g in draft.gold_slides]
    gold: list[tuple[str, int]] = st.session_state[gold_key]

    left, right = st.columns([2, 3])
    with left:
        question = st.text_area("Question", draft.question, height=100)
        answer = st.text_area("Reference answer", draft.reference_answer, height=130)

        st.markdown("**Gold Slides**")
        for key in list(gold):
            c1, c2 = st.columns([4, 1])
            c1.write(label(key))
            if (len(gold) > 1 or draft.unanswerable) and c2.button("Remove", key=f"rm-{draft.id}-{key}"):
                gold.remove(key)
                st.rerun()
        extra = st.selectbox("Add another Gold Slide", [None] + sorted(set(slides) - set(gold)),
                             format_func=lambda k: "Choose a Slide…" if k is None else label(k),
                             key=f"add-{draft.id}")
        if extra is not None and st.button("Add Gold Slide", key=f"addbtn-{draft.id}"):
            gold.append(extra)
            st.rerun()

        changed = (question.strip() != draft.question or answer.strip() != draft.reference_answer
                   or gold != [(g.lecture, g.slide) for g in draft.gold_slides])
        b1, b2 = st.columns(2)
        if b1.button("Accept with edits" if changed else "Accept", type="primary", width="stretch"):
            if changed:
                review.edit(draft.id, question=question.strip(), reference_answer=answer.strip(),
                            gold_slides=gold)
            else:
                review.accept(draft.id)
            st.rerun()
        reason = st.text_input("Reason for rejecting (optional)", key=f"why-{draft.id}")
        if b2.button("Reject", width="stretch"):
            review.reject(draft.id, reason=reason)
            st.rerun()

    with right:
        if draft.unanswerable and not gold:
            st.info("**Unanswerable Question.** The Course Material should not answer this; the "
                    "correct response is a Refusal. Accept it if no Slide answers it. If a Slide "
                    "does, add it as a Gold Slide on the left and it becomes an answerable question.")
        for key in gold:
            with st.container(border=True):
                st.markdown(f"**{label(key)}**  ·  {slides[key]['title']}")
                st.image(slide_png(*key), width="stretch")
                with st.expander("Extracted Slide text"):
                    st.text(slides[key]["text"])

st.divider()
with st.expander("Add a hand-written pair"):
    with st.form("hand-written", clear_on_submit=True):
        hq = st.text_area("Question")
        ha = st.text_area("Reference answer")
        unanswerable = st.checkbox("Unanswerable Question (the Course Material doesn't answer it)")
        hgold = st.multiselect("Gold Slides", sorted(slides), format_func=label,
                               help="Leave empty for an Unanswerable Question.")
        if st.form_submit_button("Add pair"):
            if not hq.strip() or not ha.strip():
                st.error("A question and a reference answer are both needed.")
            elif unanswerable == bool(hgold):
                st.error("An Unanswerable Question has no Gold Slides; any other question needs at least one.")
            else:
                pair = review.add_hand_written(hq.strip(), ha.strip(), list(hgold), unanswerable)
                st.success(f"Added {pair.id}.")
