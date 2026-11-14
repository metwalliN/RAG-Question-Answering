# 04: Building the Evaluation Set

**What to build:** The developer can build the 150-pair Evaluation Set:
- **Drafting:** a script drafts paraphrased candidate questions from sampled Slides with an LLM. Drafts must not copy Slide wording.
- **Review:** the developer accepts, edits or rejects each draft and labels its Gold Slides against the deduplicated Slides.
- **Hand-written pairs:** the developer adds hand-written hard questions, including Unanswerable Questions.
- **Split:** the set is split once, with a fixed seed, into a 100-pair Dev Split and a 50-pair Test Split.

The tooling is this ticket. The human labelling work happens outside it.

**Blocked by:** 02 (Ingest report: Duplicate Slides and near-empty Slides). Gold Slides must be labelled after dedupe.

**Status:** ready-for-agent

- [ ] The drafting script samples Slides and asks the LLM, through the LLM interface, for questions that paraphrase rather than copy the Slide's wording
- [ ] Drafts whose wording overlaps heavily with their source Slide are flagged for the reviewer
- [ ] The review step lets the developer accept, edit or reject each draft and set its Gold Slides, allowing several
- [ ] Gold Slides can only reference Slides present in the current ingest; unknown references are rejected
- [ ] Hand-written pairs and Unanswerable Questions (empty Gold Slides) can be added in the same file format, with origin recorded
- [ ] The split uses a fixed seed, puts Unanswerable Questions in both splits, and gives the same result every time it runs
- [ ] A validation command checks the whole Evaluation Set file (fields, Gold Slide references, split sizes) and reports problems
