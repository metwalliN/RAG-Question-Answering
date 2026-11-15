# 03: Scoring and the Baseline results table

**What to build:** The developer runs one command with a chosen split and gets a results table with Recall@5 and MRR for the Baseline Retrieval Configuration. The command reads Evaluation Pairs from a versioned file, retrieves for each question, and scores with a pure scoring function that follows ADR-0001 exactly. The Test Split is only scored when explicitly requested.

**Note:** build and test this machinery on a small sample of Evaluation Pairs (about 10 hand-made pairs in the Evaluation Set format). Real Baseline numbers are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Blocked by:** 01 (Tracer bullet: ask a question, get a cited answer)

**Status:** ready-for-agent

- [x] The Evaluation Pair record has id, question, reference answer, Gold Slides (one or more (Lecture, Slide) pairs, or empty), Unanswerable flag, origin and split, as in the spec
- [x] A pure scoring function collapses ranked Passages to distinct Anchor Slides in rank order, keeps the first 5, and computes Recall@5 and MRR over answerable pairs only
- [x] The scoring function also computes Refusal accuracy and the false Refusal rate from per-pair Refusal flags
- [x] The ladder runner takes a list of Retrieval Configurations and a split, and writes a results table with one row per configuration
- [x] Scoring the Test Split requires an explicit flag; the default is the Dev Split
- [x] Seam 2 tests with hand-made rankings cover: collapsing duplicate Anchor Slides before taking the top 5; several Gold Slides; a Gold Slide at rank 6 counting as a miss; MRR after collapsing; Unanswerable Questions excluded from Recall@5 and MRR; Refusal accuracy and false Refusal rate

## Comments

**2026-11-14:** Built test-first. Seam 2 has 5 scoring tests; a new Seam 3 (agreed with the user) has 7 ladder-runner tests; 31 tests in total, all passing. Decisions made while building:
- **MRR is MRR@5:** a Gold Slide beyond the first 5 distinct Anchor Slides scores 0, matching "collapse, keep the first 5, then score".
- **Unmeasured means empty, not 0:** a metric with nothing to measure (for example Refusal accuracy on a split with no Unanswerable Questions) is reported as "—".
- **Retrieval-only by default:** Recall@5 and MRR need no LLM calls. `--answer` calls the answering LLM (Groq's free tier, ADR-0002) for every pair to fill the Refusal columns, so it is slower and subject to rate limits.
- **A `sample` origin was added** to the Evaluation Pair record, so that the 10 unreviewed smoke-check pairs (`eval/sample_pairs.jsonl`) can never be mistaken for the real Evaluation Set.

A smoke run of the Baseline with the real bge-small model on the sample Dev Split gave Recall@5 85.7% on 7 answerable pairs. It is a smoke check only and must not be reported. Note for ticket 05: once long Slides are split, retrieval must fetch more than 5 Passages so that 5 distinct Anchor Slides remain after collapsing.
