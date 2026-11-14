"""Streamlit page: ask a question, read a cited answer. Talks only to the API."""

from __future__ import annotations

import os
import re

import requests
import streamlit as st

API_URL = os.environ.get("COURSE_QA_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Course Q&A Assistant", page_icon="📚")
st.title("Course Q&A Assistant")
st.caption("Answers come only from the course's lecture slides, with a Citation for every claim.")

question = st.text_input("Your question", placeholder="e.g. What does Fitts' law predict?")

if st.button("Ask", type="primary", disabled=not question.strip()):
    with st.spinner("Searching the slides…"):
        try:
            response = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            st.error(f"Couldn't reach the assistant: {exc}")
            st.stop()
    body = response.json()

    if body["refused"]:
        st.warning(body["answer"])
    else:
        by_marker = {c["marker"]: c for c in body["citations"]}
        # Show each [n] as a readable reference next to the claim.
        st.markdown(
            re.sub(
                r"\[(\d+)\]",
                lambda m: f"**[{m.group(1)}]**" if int(m.group(1)) in by_marker else "",
                body["answer"],
            )
        )
        st.subheader("Citations")
        for marker, c in sorted(by_marker.items()):
            with st.expander(f"[{marker}] {c['lecture']} — Slide {c['slide']}"):
                st.text(c["passage"])
