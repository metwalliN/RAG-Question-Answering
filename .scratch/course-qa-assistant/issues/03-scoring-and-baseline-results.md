# 03: Scoring and the Baseline results table

**What to build:** The developer runs one command with a chosen split and gets a results table with Recall@5 and MRR for the Baseline Retrieval Configuration. The command reads Evaluation Pairs from a versioned file, retrieves for each question, and scores with a pure scoring function that follows ADR-0001 exactly. The Test Split is only scored when explicitly requested.

**Note:** build and test this machinery on a small sample of Evaluation Pairs (about 10 hand-made pairs in the Evaluation Set format). Real Baseline numbers are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Blocked by:** 01 (Tracer bullet: ask a question, get a cited answer)

**Status:** ready-for-agent

- [ ] The Evaluation Pair record has id, question, reference answer, Gold Slides (one or more (Lecture, Slide) pairs, or empty), Unanswerable flag, origin and split, as in the spec
- [ ] A pure scoring function collapses ranked Passages to distinct Anchor Slides in rank order, keeps the first 5, and computes Recall@5 and MRR over answerable pairs only
- [ ] The scoring function also computes Refusal accuracy and the false Refusal rate from per-pair Refusal flags
- [ ] The ladder runner takes a list of Retrieval Configurations and a split, and writes a results table with one row per configuration
- [ ] Scoring the Test Split requires an explicit flag; the default is the Dev Split
- [ ] Seam 2 tests with hand-made rankings cover: collapsing duplicate Anchor Slides before taking the top 5; several Gold Slides; a Gold Slide at rank 6 counting as a miss; MRR after collapsing; Unanswerable Questions excluded from Recall@5 and MRR; Refusal accuracy and false Refusal rate
