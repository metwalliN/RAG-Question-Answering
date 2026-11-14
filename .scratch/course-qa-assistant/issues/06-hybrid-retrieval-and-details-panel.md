# 06: Hybrid retrieval and the Retrieval details panel

**What to build:** A hybrid Retrieval Configuration fuses BM25 and dense rankings, and the ladder shows what keyword matching adds. In the UI, an expandable "Retrieval details" panel under each answer shows the retrieved Passages with their BM25 and dense scores, and the timing breakdown. This is useful for debugging and demos.

**Blocked by:** 03 (Scoring and the Baseline results table)

**Note:** build and test this on the small sample of Evaluation Pairs from ticket 03. Real ladder numbers for the hybrid configuration are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Status:** ready-for-agent

- [ ] Ingest builds a BM25 index alongside the dense index
- [ ] The hybrid configuration fuses BM25 and dense rankings with fusion weights and candidate depth set in config
- [ ] Each entry in the `/ask` response's `retrieval` list carries `scores {bm25, dense}` where present
- [ ] The Streamlit page has an expandable "Retrieval details" panel showing each retrieved Passage with its Lecture, Slide and scores, plus `timings_ms`
- [ ] The ladder runner produces a hybrid row, built on the passage-building option set in its config
- [ ] Seam 1 tests check that a question matching a Passage only by keyword is retrieved in hybrid mode, and that the response's scores are present
