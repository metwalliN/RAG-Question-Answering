# 05: Chunking variants

**What to build:** The developer runs the ladder and sees the four passage-building options side by side in the results table, so that "tuned chunking" is a measured comparison. Each option is its own Retrieval Configuration, all dense-only. In every option each Passage has exactly one Anchor Slide, and neighbouring Slides only add context (ADR-0001).

**Blocked by:** 03 (Scoring and the Baseline results table)

**Note:** build and test this on the small sample of Evaluation Pairs from ticket 03. Real ladder numbers for the chunking options are recorded only after ticket 04 delivers the full Evaluation Set. Numbers from the sample are smoke checks and must not be reported.

**Status:** ready-for-agent

- [ ] Option 1: one Slide per Passage (the Baseline)
- [ ] Option 2: a 2-Slide window, with the Anchor Slide plus the previous Slide as context
- [ ] Option 3: a 3-Slide window, with the Anchor Slide plus one neighbour on each side as context
- [ ] Option 4: one Slide per Passage, with long Slides split into several Passages that share the same Anchor Slide; the length limit is set in config
- [ ] Windows don't cross Lecture boundaries
- [ ] Citations always name the Anchor Slide, whatever the option
- [ ] Ingest builds Passages for whichever option the Retrieval Configuration names
- [ ] The ladder runner produces one row per option
- [ ] Seam 1 tests run against every option and assert that each Passage has exactly one Anchor Slide and that window context never changes the Anchor
